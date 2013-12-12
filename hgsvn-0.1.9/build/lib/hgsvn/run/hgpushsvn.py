"""hgpushsvn must be run in a repository created by hgimportsvn. It pushes
local Mercurial changesets one by one or optionally collapsed into a single
commit back to the SVN repository.

"""

import codecs
import os
import stat
import sys
import re
from optparse import OptionParser

from hgsvn import ui
from hgsvn.common import (
    run_hg, run_svn, hg_switch_branch, hgsvn_private_dir,
    check_for_applied_patches, get_encoding
    )
from hgsvn.errors import ExternalCommandFailed, EmptySVNLog
from hgsvn.run.common import run_parser, display_parser_error
from hgsvn.run.common import locked_main
from hgsvn.svnclient import get_svn_info, get_svn_status


def map_svn_rev_to_hg(svn_rev, hg_rev="tip", local=False):
    """
    Record the mapping from an SVN revision number and an hg revision (default "tip").
    """
    args = ["tag"]
    if local:
        args.append("-l")
    args.extend(["-r", strip_hg_rev(hg_rev), "svn.%d" % svn_rev])
    run_hg(args)

def strip_hg_rev(rev_string):
    """
    Given a string identifying an hg revision, return a string identifying the
    same hg revision and suitable for revrange syntax (r1:r2).
    """
    if ":" in rev_string:
        return rev_string.rsplit(":", 1)[1].strip()
    return rev_string.strip()

def get_hg_cset(rev_string):
    """
    Given a string identifying an hg revision, get the canonical changeset ID.
    """
    args = ["log", "--template", r"{rev}:{node|short}\n", "-r", rev_string]
    return run_hg(args).strip()

def get_hg_revs(first_rev, svn_branch, last_rev="tip"):
    """
    Get a chronological list of revisions (changeset IDs) between the two
    revisions (included).
    """
    args = ["log", "--template", r'{rev}:{node|short}\n', "-b", svn_branch,
            '--limit', '1000', '--follow',
            "-r", "%s:%s" % (strip_hg_rev(first_rev),
                             strip_hg_rev(last_rev))]
    out = run_hg(args)
    return [strip_hg_rev(s) for s in out.splitlines()]

def get_pairs(l):
    """
    Given a list, return a list of consecutive pairs of values.
    """
    return [(l[i], l[i+1]) for i in xrange(len(l) - 1)]

def get_hg_changes(rev_string):
    """
    Get paths of changed files from a previous revision.
    Returns a tuple of (added files, removed files, modified files, copied files)
    Copied files are dict of (dest=>src), others are lists.
    """
    args = ["st", "-armC", "--rev", rev_string]
    out = run_hg(args, output_is_locale_encoding=True)
    added = []
    removed = []
    modified = []
    copied = {}
    skipnext = False
    for line in out.splitlines():
        st = line[0]
        path = line[2:]
        if st == 'A':
            added.append(path)
            lastadded=path
        elif st == 'R':
            removed.append(path)
        elif st == 'M':
            modified.append(path)
        elif st == ' ':
            added.remove(lastadded)
            copied[lastadded] = path
    #print "added:", added
    #print "removed:", removed
    #print "modified:", modified
    return added, removed, modified, copied

def get_ordered_dirs(l):
    """
    Given a list of relative file paths, return an ordered list of dirs such that
    creating those dirs creates the directory structure necessary to hold those files.
    """
    dirs = set()
    for path in l:
        while True:
            path = os.path.dirname(path)
            if not path or path in dirs:
                break
            dirs.add(path)
    return list(sorted(dirs))

def get_hg_csets_description(start_rev, end_rev):
    """Get description of a given changeset range."""
    return run_hg(["log", "--template", r"{desc|strip}\n", "--follow", "--rev",
                   start_rev+":"+end_rev, "--prune", start_rev])

def get_hg_cset_description(rev_string):
    """Get description of a given changeset."""
    return run_hg(["log", "--template", "{desc|strip}", "-r", rev_string])

def get_hg_log(start_rev, end_rev):
    """Get log messages for given changeset range."""

    log_args=["log", "--verbose", "--follow", "--rev", start_rev+":"+end_rev, "--prune", start_rev]
    return run_hg(log_args)

def get_svn_subdirs(top_dir):
    """
    Given the top directory of a working copy, get the list of subdirectories
    (relative to the top directory) tracked by SVN.
    """
    subdirs = []
    def _walk_subdir(d):
        svn_dir = os.path.join(top_dir, d, ".svn")
        if os.path.exists(svn_dir) and os.path.isdir(svn_dir):
            subdirs.append(d)
            for f in os.listdir(os.path.join(top_dir, d)):
                d2 = os.path.join(d, f)
                if f != ".svn" and os.path.isdir(os.path.join(top_dir, d2)):
                    _walk_subdir(d2)
    _walk_subdir(".")
    return subdirs

def strip_nested_removes(targets):
    """Strip files within removed folders and return a cleaned up list."""
    # We're going a safe way here: "svn info" fails on items within removed
    # dirs.
    clean_targets = []
    for target in targets:
        try:
            run_svn(['info', '--xml', target], mask_atsign=True)
        except ExternalCommandFailed, err:
            ui.status(str(err), level=ui.DEBUG)
            continue
        clean_targets.append(target)
    return clean_targets

def cleanup_svn_unversioned(files):
    svn_status = get_svn_status(".")
    for entry in svn_status:
        if(entry['type'] == 'unversioned') and entry['path'] in files:
            files.remove(entry['path'])
    return files

def adjust_executable_property(files):
    execflags = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    svn_map = {}
    for fname in files:
        if run_svn(['propget', 'svn:executable', fname],
                   mask_atsign=True).strip():
            svn_map[fname] = True
        else:
            svn_map[fname] = False
    for fname in files:
        m = os.stat(fname).st_mode & 0777
        is_exec = bool(m & execflags)
        if is_exec and not svn_map[fname]:
            run_svn(['propset', 'svn:executable', 'ON', fname],
                    mask_atsign=True)
        elif not is_exec and svn_map[fname]:
            run_svn(['propdel', 'svn:executable', fname], mask_atsign=True)

def do_svn_copy(src, dest):
    """
    Call Svn copy command to record copying file src to file dest.
    If src is present then backup src before other tasks.
    Before issuing copy command move dest to src and remove src after
    """
    backup_src = ''
    if os.path.exists(src):
        backup_src = os.path.join(hgsvn_private_dir, "hgpushsvn_backup.tmp")
        os.rename(src, backup_src)

    try:
        try:
            # We assume that src is cotrolled by svn
            os.rename(dest, src)

            # Create svn subdirectories if needed
            # We know that subdirectories themselves are present
            # as dest is present
            pattern = re.compile(r"[/\\]")
            pos = 0
            while(True):
                match = pattern.search(dest, pos + 1)
                if match == None:
                    break

                pos = match.start()
                run_svn(['add', '--depth=empty'], [dest[:pos]],
                        mask_atsign=True)
                pos = match.end() - 1

            # Do the copy itself
            run_svn(['copy', src, dest], mask_atsign=True)
        except ExternalCommandFailed:
            # Revert rename
            os.rename(src, dest)
    finally:
        if os.path.isfile(src):
            os.remove(src)

        if(backup_src):
            os.rename(backup_src, src)

def hg_push_svn(start_rev, end_rev, edit, username, password, cache):
    """
    Commit the changes between two hg revisions into the SVN repository.
    Returns the SVN revision object, or None if nothing needed checking in.
    """
    added, removed, modified, copied = get_hg_changes(start_rev+':'+end_rev)

    # Before replicating changes revert directory to previous state...
    run_hg(['revert', '--all', '--no-backup', '-r', end_rev])

    # ... and restore .svn directories, if we lost some of them due to removes
    run_svn(['revert', '--recursive', '.'])

    # Do the rest over up-to-date working copy
    # Issue 94 - moved this line to prevent do_svn_copy crashing when its not the first changeset
    run_hg(["up", "-C", end_rev])

    # Record copyies into svn
    for dest, src in copied.iteritems():
        do_svn_copy(src,dest)

    # Add new files and dirs
    if added:
        bulk_args = get_ordered_dirs(added) + added
        run_svn(["add", "--depth=empty"], bulk_args,
                mask_atsign=True)
    removed = cleanup_svn_unversioned(removed)
    modified = cleanup_svn_unversioned(modified)
    # Remove old files and empty dirs
    if removed:
        empty_dirs = [d for d in reversed(get_ordered_dirs(removed))
                      if not run_hg(["st", "-c", "%s" %d])]
        # When running "svn rm" all files within removed folders needs to
        # be removed from "removed". Otherwise "svn rm" will fail. For example
        # instead of "svn rm foo/bar foo" it should be "svn rm foo".
        # See issue15.
        svn_removed = strip_nested_removes(removed + empty_dirs)
        run_svn(["rm"], svn_removed, mask_atsign=True)
    if added or removed or modified:
        svn_sep_line = "--This line, and those below, will be ignored--\n"
        adjust_executable_property(added+modified)  # issue24
        description = get_hg_csets_description(start_rev, end_rev)
        fname = os.path.join(hgsvn_private_dir, 'commit-%s.txt' % end_rev)
        lines = description.splitlines()+[""]
        lines.append(svn_sep_line)
        lines.append("To cancel commit just delete text in top message part")
        lines.append("")
        lines.append("Changes to be committed into svn:")
        lines.extend([item.decode("utf-8")
                      for item in run_svn(["st", "-q"]).splitlines()])
        lines.append("")
        lines.append(("These changes are produced from the following "
                      "Hg changesets:"))
        lines.extend(get_hg_log(start_rev, end_rev).splitlines())
        f = codecs.open(fname, "wb", "utf-8")
        f.write(os.linesep.join(lines))
        f.close()

        try:
            if edit:
                editor=(os.environ.get("HGEDITOR") or
                        os.environ.get("SVNEDITOR") or
                        os.environ.get("VISUAL") or
                        os.environ.get("EDITOR", "vi"))

                rc = os.system("%s \"%s\"" % (editor, fname) )
                if(rc):
                    raise ExternalCommandFailed("Can't launch editor")

                empty = True

                f=open(fname, "r")
                for line in f:
                    if(line == svn_sep_line):
                        break

                    if(line.strip() != ""):
                        empty = False
                        break
                f.close()

                if(empty):
                    raise EmptySVNLog("Commit cancelled by user\n")

            svn_rev = None
            svn_commands = ["commit", "-F", fname, "--encoding", get_encoding()]
            if username is not None:
                svn_commands += ["--username", username]
            if password is not None:
                svn_commands += ["--password", password]
            if cache:
                svn_commands.append("--no-auth-cache")
            out = run_svn(svn_commands)

            outlines = out.splitlines()
            outlines.reverse()
            for line in outlines:
                # one of the last lines holds the revision.
                # The previous approach to set LC_ALL to C and search
                # for "Committed revision XXX" doesn't work since
                # svn is unable to convert filenames containing special
                # chars:
                # http://svnbook.red-bean.com/en/1.2/svn.advanced.l10n.html
                match = re.search("(\d+)", line)
                if match:
                    svn_rev = int(match.group(1))
                    break

            return svn_rev
        finally:
            # Exceptions are handled by main().
            os.remove(fname)
    else:
        print "*", "svn: nothing to do"
        return None


def real_main(options, args):
    if run_hg(["st", "-m"]):
        print ("There are uncommitted changes. Either commit them or put "
               "them aside before running hgpushsvn.")
        return 1
    if check_for_applied_patches():
        print ("There are applied mq patches. Put them aside before "
               "running hgpushsvn.")
        return 1
    svn_info = get_svn_info(".")
    svn_current_rev = svn_info["last_changed_rev"]
    # e.g. u'svn://svn.twistedmatrix.com/svn/Twisted'
    repos_url = svn_info["repos_url"]
    # e.g. u'svn://svn.twistedmatrix.com/svn/Twisted/branches/xmpp-subprotocols-2178-2'
    wc_url = svn_info["url"]
    assert wc_url.startswith(repos_url)
    # e.g. u'/branches/xmpp-subprotocols-2178-2'
    wc_base = wc_url[len(repos_url):]

    svn_branch = wc_url.split("/")[-1]

    # Get remote SVN info
    svn_greatest_rev = get_svn_info(wc_url)['last_changed_rev']

    if svn_greatest_rev != svn_current_rev:
        # We can't go on if the pristine branch isn't up to date.
        # If the pristine branch lacks some revisions from SVN we are not
        # able to pull them afterwards.
        # For example, if the last SVN revision in out hgsvn repository is
        # r100 and the latest SVN revision is r101, hgpushsvn would create
        # a tag svn.102 on top of svn.100, but svn.101 isn't in hg history.
        print ("Branch '%s' out of date. Run 'hgpullsvn' first."
               % svn_branch)
        return 1

    # Switch branches if necessary.
    orig_branch = run_hg(["branch"]).strip()
    if orig_branch != svn_branch:
        if not hg_switch_branch(orig_branch, svn_branch):
            return 1

    hg_start_rev = "svn.%d" % svn_current_rev
    hg_revs = None
    try:
        hg_start_cset = get_hg_cset(hg_start_rev)
    except RuntimeError:
        if not options.force:
            raise
        hg_start_cset = get_hg_cset("0")
        print "Warning: revision '%s' not found, forcing to first rev '%s'" % (
            hg_start_rev, hg_start_cset)
    else:
        if not options.collapse:
            hg_revs = get_hg_revs(hg_start_cset, svn_branch)
    if hg_revs is None:
        hg_revs = [strip_hg_rev(hg_start_cset), strip_hg_rev(get_hg_cset("tip"))]

    pushed_svn_revs = []
    try:
        if options.dryrun:
            print "Outgoing revisions that would be pushed to SVN:"
        try:
            for prev_rev, next_rev in get_pairs(hg_revs):
                if not options.dryrun:
                    if not options.edit:
                        ui.status("Committing changes up to revision %s",
                                    get_hg_cset(next_rev))
                    username = options.username
                    if options.keep_author:
                        username = run_hg(["log", "-r", next_rev,
                                            "--template", "{author}"])
                    svn_rev = hg_push_svn(prev_rev, next_rev,
                                            edit=options.edit,
                                            username=username,
                                            password=options.password,
                                            cache=options.cache)
                    if svn_rev:
                        # Issue 95 - added update to prevent add/modify/delete crash
                        run_svn(["up"])
                        map_svn_rev_to_hg(svn_rev, next_rev, local=True)
                        pushed_svn_revs.append(svn_rev)
                else:
                    print run_hg(["log", "-r", next_rev,
                              "--template", "{rev}:{node|short} {desc}"])
        except:
            # TODO: Add --no-backup to leave a "clean" repo behind if something
            #   fails?
            run_hg(["revert", "--all"])
            raise

    finally:
        work_branch = orig_branch or svn_branch
        if work_branch != svn_branch:
            run_hg(["up", "-C", work_branch])
            run_hg(["branch", work_branch])

    if pushed_svn_revs:
        if len(pushed_svn_revs) == 1:
            msg = "Pushed one revision to SVN: "
        else:
            msg = "Pushed %d revisions to SVN: " % len(pushed_svn_revs)
        run_svn(["up", "-r", pushed_svn_revs[-1]])
        ui.status("%s %s", msg, ", ".join(str(x) for x in pushed_svn_revs))
        for line in run_hg(["st"]).splitlines():
            if line.startswith("M"):
                ui.status(("Mercurial repository has local changes after "
                           "SVN update."))
                ui.status(("This may happen with SVN keyword expansions."))
                break
    elif not options.dryrun:
        ui.status("Nothing to do.")

def main():
    # Defined as entry point. Must be callable without arguments.
    usage = "usage: %prog [-cf]"
    parser = OptionParser(usage)
    parser.add_option("-f", "--force", default=False, action="store_true",
                      dest="force",
                      help="push even if no hg tag found for current SVN rev.")
    parser.add_option("-c", "--collapse", default=False, action="store_true",
                      dest="collapse",
                      help="collapse all hg changesets in a single SVN commit")
    parser.add_option("-n", "--dry-run", default=False, action="store_true",
                      dest="dryrun",
                      help="show outgoing changes to SVN without pushing them")
    parser.add_option("-e", "--edit", default=False, action="store_true",
                      dest="edit",
                      help="edit commit message using external editor")
    parser.add_option("-u", "--username", default=None, action="store", type="string",
                      dest="username",
                      help="specify a username ARG as same as svn --username")
    parser.add_option("-p", "--password", default=None, action="store", type="string",
                      dest="password",
                      help="specify a password ARG as same as svn --password")
    parser.add_option("--no-auth-cache", default=False, action="store_true",
                      dest="cache",
                      help="Prevents caching of authentication information")
    parser.add_option("--keep-author", default=False, action="store_true",
                      dest="keep_author",
                      help="keep the author when committing to SVN")
    (options, args) = run_parser(parser, __doc__)
    if args:
        display_parser_error(parser, "incorrect number of arguments")
    return locked_main(real_main, options, args)

if __name__ == "__main__":
    sys.exit(main() or 0)

