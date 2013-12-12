
from hgsvn import ui
from hgsvn.errors import ExternalCommandFailed, HgSVNError

import os
import locale
from datetime import datetime
import time
from subprocess import Popen, PIPE, STDOUT
import shutil
import stat
import sys
import traceback

try:
    import commands
except ImportError:
    commands = None

class _SimpleFileLock(object):

    def __init__(self, filename, timeout=None):
        self.file = filename
        self.lock()

    def lock(self):
        if os.path.exists(self.file):
            raise LockHeld("Lock file exists.")
        open(self.file, "wb").close()

    def release(self):
        if os.path.exists(self.file):
            os.remove(self.file)


class _LockHeld(Exception):
    pass


# We import the lock logic from Mercurial if it is available, and fall back
# to a dummy (always successful) lock if not.
try:
    from mercurial.lock import lock as _lock
    try:
        from mercurial.error import LockHeld
    except ImportError:
        # LockHeld was defined in mercurial.lock in Mercurial < 1.2
        from mercurial.lock import LockHeld

except ImportError:
    _lock = _SimpleFileLock
    LockHeld = _LockHeld


hgsvn_private_dir = ".hgsvn"
hgsvn_lock_file = "lock"

if "SVN_ASP_DOT_NET_HACK" in os.environ:
    svn_private_dir = "_svn"
else:
    svn_private_dir = '.svn'

hg_commit_prefix = "[svn r%d] "
# This seems sufficient for excluding all .svn (sub)directories
hg_exclude_options = ["-X", svn_private_dir, "-X", "**/%s" % svn_private_dir]

# Windows compatibility code by Bill Baxter
if os.name == "nt":
    def find_program(name):
        """
        Find the name of the program for Popen.
        Windows is finnicky about having the complete file name. Popen
        won't search the %PATH% for you automatically.
        (Adapted from ctypes.find_library)
        """
        # See MSDN for the REAL search order.
        base, ext = os.path.splitext(name)
        if ext:
            exts = [ext]
        else:
            exts = ['.bat', '.exe']
        for directory in os.environ['PATH'].split(os.pathsep):
            for e in exts:
                fname = os.path.join(directory, base + e)
                if os.path.exists(fname):
                    return fname
        return name
else:
    def find_program(name):
        """
        Find the name of the program for Popen.
        On Unix, popen isn't picky about having absolute paths.
        """
        return name


def _rmtree_error_handler(func, path, exc_info):
    """
    Error handler for rmtree. Helps removing the read-only protection under
    Windows (and others?).
    Adapted from http://www.proaxis.com/~darkwing/hot-backup.py
    and http://patchwork.ozlabs.org/bazaar-ng/patch?id=4243
    """
    if func in (os.remove, os.rmdir) and os.path.exists(path):
        # Change from read-only to writeable
        os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
        func(path)
    else:
        # something else must be wrong...
        raise

def rmtree(path):
    """
    Wrapper around shutil.rmtree(), to provide more error-resistent behaviour.
    """
    return shutil.rmtree(path, False, _rmtree_error_handler)


locale_encoding = locale.getpreferredencoding()

def get_encoding():
    return locale_encoding

def shell_quote(s):
    if os.name == "nt":
        q = '"'
    else:
        q = "'"
    return q + s.replace('\\', '\\\\').replace("'", "'\"'\"'") + q

def _run_raw_command(cmd, args, fail_if_stderr=False):
    cmd_string = "%s %s" % (cmd,  " ".join(map(shell_quote, args)))
    ui.status("* %s", cmd_string, level=ui.DEBUG)
    try:
        pipe = Popen([cmd] + args, executable=cmd, stdout=PIPE, stderr=PIPE)
    except OSError:
        etype, value = sys.exc_info()[:2]
        raise ExternalCommandFailed(
            "Failed running external program: %s\nError: %s"
            % (cmd_string, "".join(traceback.format_exception_only(etype, value))))
    out, err = pipe.communicate()
    if "nothing changed" == out.strip(): # skip this error
        return out
    if pipe.returncode != 0 or (fail_if_stderr and err.strip()):
        raise ExternalCommandFailed(
            "External program failed (return code %d): %s\n%s\n%s"
            % (pipe.returncode, cmd_string, err, out))
    return out

def _run_raw_shell_command(cmd):
    ui.status("* %s", cmd, level=ui.DEBUG)
    st, out = commands.getstatusoutput(cmd)
    if st != 0:
        raise ExternalCommandFailed(
            "External program failed with non-zero return code (%d): %s\n%s"
            % (st, cmd, out))
    return out

def run_command(cmd, args=None, bulk_args=None, encoding=None, fail_if_stderr=False):
    """
    Run a command without using the shell.
    """
    args = args or []
    bulk_args = bulk_args or []
    def _transform_arg(a):
        if isinstance(a, unicode):
            a = a.encode(encoding or locale_encoding or 'UTF-8')
        elif not isinstance(a, str):
            a = str(a)
        return a

    cmd = find_program(cmd)
    if not bulk_args:
        return _run_raw_command(cmd, map(_transform_arg, args), fail_if_stderr)
    # If one of bulk_args starts with a slash (e.g. '-foo.php'),
    # hg and svn will take this as an option. Adding '--' ends the search for
    # further options.
    for a in bulk_args:
        if a.strip().startswith('-'):
            args.append("--")
            break
    max_args_num = 254
    i = 0
    out = ""
    while i < len(bulk_args):
        stop = i + max_args_num - len(args)
        sub_args = []
        for a in bulk_args[i:stop]:
            sub_args.append(_transform_arg(a))
        out += _run_raw_command(cmd, args + sub_args, fail_if_stderr)
        i = stop
    return out

def run_shell_command(cmd, args=None, bulk_args=None, encoding=None):
    """
    Run a shell command, properly quoting and encoding arguments.
    Probably only works on Un*x-like systems.
    """
    def _quote_arg(a):
        if isinstance(a, unicode):
            a = a.encode(encoding or locale_encoding)
        elif not isinstance(a, str):
            a = str(a)
        return shell_quote(a)

    if args:
        cmd += " " + " ".join(_quote_arg(a) for a in args)
    max_args_num = 254
    i = 0
    out = ""
    if not bulk_args:
        return _run_raw_shell_command(cmd)
    while i < len(bulk_args):
        stop = i + max_args_num - len(args)
        sub_args = []
        for a in bulk_args[i:stop]:
            sub_args.append(_quote_arg(a))
        sub_cmd = cmd + " " + " ".join(sub_args)
        out += _run_raw_shell_command(sub_cmd)
        i = stop
    return out

def run_hg(args=None, bulk_args=None, output_is_locale_encoding=False):
    """
    Run a Mercurial command, returns the (unicode) output.
    """
    default_args = ["--encoding", "utf-8"]
    output = run_command("hg", args=default_args + (args or []),
        bulk_args=bulk_args)
    if output_is_locale_encoding:
        enc = locale_encoding
    else:
        enc = 'utf-8'
    return output.decode(enc)

def run_svn(args=None, bulk_args=None, fail_if_stderr=False,
            mask_atsign=False):
    """
    Run an SVN command, returns the (bytes) output.
    """
    if mask_atsign:
        # The @ sign in Subversion revers to a pegged revision number.
        # SVN treats files with @ in the filename a bit special.
        # See: http://stackoverflow.com/questions/1985203
        for idx in range(len(args)):
            if "@" in args[idx] and args[idx][0] not in ("-", '"'):
                args[idx] = "%s@" % args[idx]
        if bulk_args:
            for idx in range(len(bulk_args)):
                if ("@" in bulk_args[idx]
                    and bulk_args[idx][0] not in ("-", '"')):
                    bulk_args[idx] = "%s@" % bulk_args[idx]
    return run_command("svn",
        args=args, bulk_args=bulk_args, fail_if_stderr=fail_if_stderr)

def skip_dirs(paths, basedir="."):
    """
    Skip all directories from path list, including symbolic links to real dirs.
    """
    # NOTE: both tests are necessary (Cameron Hutchison's patch for symbolic
    # links to directories)
    return [p for p in paths
        if not os.path.isdir(os.path.join(basedir, p))
        or os.path.islink(os.path.join(basedir, p))]


def hg_commit_from_svn_log_entry(entry, files=None):
    """
    Given an SVN log entry and an optional sequence of files, turn it into
    an appropriate hg changeset on top of the current branch.
    """
    # This will use the local timezone for displaying commit times
    timestamp = int(entry['date'])
    hg_date = str(datetime.fromtimestamp(timestamp))
    # Uncomment this one one if you prefer UTC commit times
    #hg_date = "%d 0" % timestamp
    message = (hg_commit_prefix % entry['revision']) + entry['message'].lstrip()
    commit_file = None
    try:
        commit_file = os.path.join(hgsvn_private_dir,
            "commit-%r.txt" % entry['revision'])
        f = open(commit_file, "wb")
        f.write(message.encode('utf-8'))
        f.close()
        msg_options = ["-l", commit_file]
        # the -m will now work on windows with utf-8 encoding argument
        # the CreateProcess win32api convert bytes to uicode by locale codepage
        # msg.encode('utf-8').decode('cp932').encode('cp932').decode('utf-8')
        options = ["ci"] + msg_options + ["-d", hg_date]
        if entry['author']:
            options.extend(["-u", entry['author']])
        if files:
            run_hg(options, files)
        else:
            run_hg(options)
    except ExternalCommandFailed:
        # When nothing changed on-disk (can happen if an SVN revision only
        # modifies properties of files, not their contents), hg ci will fail
        # with status code 1 (and stderr "nothing changed")
        if run_hg(['st', '-mard'], output_is_locale_encoding=True).strip():
            raise
    finally:
        if commit_file and os.path.exists(commit_file):
            os.remove(commit_file)
    try:
        hg_tag_svn_rev(entry['revision'])
    except:
        # Rollback the transaction.
        last_rev = get_svn_rev_from_hg()
        if last_rev != entry['revision']:
            run_hg(["rollback"])
        raise

def hg_tag_svn_rev(rev_number):
    """
    Put a local hg tag according to the SVN revision.
    """
    run_hg(["tag", "-l", "svn.%d" % rev_number])

def get_svn_rev_from_hg():
    """
    Get the current SVN revision as reflected by the hg working copy,
    or None if no match found.
    """
    tags = run_hg(['parents', '--template', '{tags}']).strip().split()
    revs = [int(tag[4:]) for tag in tags if tag.startswith('svn.')]
    # An hg changeset can map onto several SVN revisions, for example if a
    # revision only changed SVN properties.
    if revs:
        return max(revs)
    return None

def fixup_hgsvn_dir(basedir='.'):
    """
    Create the hgsvn directory if it does not exist. Useful when using
    repos created by a previous version.
    """
    target = os.path.join(basedir, hgsvn_private_dir)
    if not os.path.exists(target):
        os.mkdir(target)

def get_hgsvn_lock(basedir='.'):
    """
    Get a lock using the hgsvn lock file.
    """
    return _lock(os.path.join(basedir, hgsvn_private_dir, hgsvn_lock_file),
        timeout=0)


def change_to_rootdir():
    """Changes working directory to root of checkout.

    Raises HgSVNError if the current working directory isn't a Mercurial
    repository.
    """
    try:
        root = run_hg(["root"]).strip()
    except ExternalCommandFailed, err:
        raise HgSVNError('No Mercurial repository found.')
    os.chdir(root)


def hg_is_clean(current_branch):
    """Returns False if the local Mercurial repository has
       uncommitted changes."""
    if run_hg(['st', '-mard'], output_is_locale_encoding=True).strip():
        ui.status(("\nThe Mercurial working copy contains pending changes "
                   "in branch '%s'!\n"
                   "Please either commit or discard them before running "
                   "'%s' again."
                   % (current_branch, get_script_name())),
                  level=ui.ERROR)
        return False
    return True


def get_script_name():
    """Helper to return the name of the command line script that was called."""
    return os.path.basename(sys.argv[0])


def hg_switch_branch(current_branch, new_branch):
    """Safely switch the Mercurial branch.

    The function will only switch to new_branch iff there are no uncommitted
    changed in the  current branch.

    True is returned if the switch was successful otherwise False.
    """
    hg_branches = [l.split()[0] for l in run_hg(["branches"]).splitlines()]
    if new_branch in hg_branches:
        # We want to run "hg up -C" (to force changing branches) but we
        # don't want to erase uncommitted changes.
        if not hg_is_clean(current_branch):
            return False
        run_hg(['up', '-C', new_branch])
    run_hg(["branch", new_branch])
    return True


def check_for_applied_patches():
    """Check for applied mq patches.

    Returns ``True`` if any mq patches are applied, otherwise ``False``.
    """
    try:
        out = run_hg(["qapplied"])
        patches = [s.strip() for s in out.splitlines()]
        if len(patches) > 0:
            return True
    except ExternalCommandFailed, err:
        pass
    return False

def once_or_more(desc, retry, function, *args, **kwargs):
    """Try executing the provided function at least once.

    If ``retry`` is ``True``, running the function with the given arguments
    if an ``Exception`` is raised. Otherwise, only run the function once.

    The string ``desc`` should be set to a short description of the operation.
    """
    while True:
        try:
            return function(*args, **kwargs)
        except Exception, e:
            ui.status('%s failed: %s', desc, str(e))
            if retry:
                ui.status('Trying %s again...', desc)
                continue
            else:
                raise
