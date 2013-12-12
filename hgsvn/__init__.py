"""
-------
Summary
-------

This set of scripts allows to work locally on Subversion-managed projects
using the Mercurial distributed version control system.

Why use Mercurial ? You can do local (disconnected) work, pull the latest
changes from the SVN server, manage private branches, submit patches to project
maintainers, etc. And of course you have fast local operations like "hg log",
"hg annotate"...

Three scripts are provided:

* ``hgimportsvn`` initializes an SVN checkout which is also a Mercurial
  repository.
* ``hgpullsvn`` pulls the latest changes from the SVN repository, and updates
  the Mercurial repository accordingly. It can be run multiple times.
* ``hgpushsvn`` pushes your local Mercurial commits back to the SVN repository.

-------
Example
-------

Making a checkout of the Django_ trunk::

    $ mkdir django && cd django
      # Make SVN checkout, initialize hg repository with first SVN revision
    $ hgimportsvn http://code.djangoproject.com/svn/django/trunk/
    $ cd trunk
      # Pull all history from SVN, creating a new hg changeset for each SVN rev
    $ hgpullsvn

Then make your changes and use the "hg" commands to commit them locally.
If you have commit privileges you can push back your changes to the SVN
repository::

    $ hgpushsvn

If you want to see what will be pushed back to SVN, use the "-n/--dry-run"
flag. This is much like the "hg outgoing" command::

    $ hgpushsvn --dry-run

.. _Django: http://www.djangoproject.com

-------
Install
-------

Just type ``easy_install hgsvn``. If easy_install is not available on
your computer, download and uncompress the source tarball, then type
``python setup.py install``. Type ``python setup.py install --help``
for additional options.

*Note:* hgsvn makes use of the ElementTree library. It is bundled by default
with Python 2.5, and the setup script should install it automatically for you
if you are using Python 2.4. However, if you get some error messages, you might
have to install it manually (at least one user reported he had to).

Unstable (development) version
------------------------------

Just run ``hg clone http://bitbucket.org/andialbrecht/hgsvn hgsvn`` and you'll
get the contents of the development repository.

--------
Features
--------

Graceful operation
------------------

``hgpullsvn`` asks for SVN log entries in chunks, so that pulling history does
not put the remote server on its knees.

``hgpullsvn`` can be interrupted at any time, and run again later: you can pull
history incrementally.

Metadata
--------

hgsvn reflects commit times (using the local timezone) and commit author names.
Commit messages can contain Unicode characters. File copies and renames as
reflected as well, provided they occur inside the branch.

Tags
----

``hgpullsvn`` tags each new Mercurial changeset with a local tag named
'svn.123' where 123 is the number of the corresponding SVN revision.
Local tags were chosen because they don't pollute the hg log with
superfluous entries, and also because SVN revision numbers are only
meaningful for a specific branch: there is no use propagating them
(IMHO).

Named branches
--------------

These scripts encourage the use of named branches. All updates using
``hgpullsvn`` are made in the branch named from the last component of the
SVN URL (e.g., if the SVN URL is svn://server/myproj/branches/feature-ZZZ,
``hgpullsvn`` will create and use the named branch 'feature-ZZZ').

You can thus do local development using your own named branches. When you
want to fetch latest history from the SVN repository, simply use ``hgpullsvn``
which will update to the original (pristine) branch, leaving your local work
intact (you can then merge by yourself if your want).

This also means that ``hg di -r name-of-pristine-branch`` will immediately
give you a patch against the pristine branch, which you can submit to the
project maintainers.

(Note: in a non-trivial setup where you work on several features or bugfixes,
you will clone the pristine repository for each separate piece of work,
which will still give you the benefit of named branches for quickly generating
patches).

Detecting parent repository
---------------------------

If the SVN URL has been created by copying from another SVN URL (this is the
standard method for branch creation), ``hgimportsvn`` tries to find an hgsvn
repository corresponding to the parent SVN URL.
It then creates the new repository by cloning this repository at the revision
immediately before the creation of the SVN branch.

In other words, let's say you are operating from myworkdir/. In myworkdir/trunk,
you already have an hgsvn repository synced from svn://server/myproj/trunk.
You then ``hgimport svn://server/myproj/branches/new-feature``. It will find
that the 'new-feature' branch has been created by copying from 'trunk'
at rev. 1138. It will thus create the 'new-feature' hg repository by cloning
from the 'trunk' repository at the revision immediately preceding rev. 1138:
for example rev. 1135, identified by the local tag 'svn.1135'.

This means you will have an hgsvn repository containing two named branches:
'trunk' for all the changesets in the trunk before rev. 1138, and 'new-feature'
for all the changesets in the SVN branch (therefore, after rev. 1138).
This way, you can easily track how the branch diverges from the trunk, but also
do merges, etc.

-----------
Limitations
-----------

SVN externals are purposefully ignored and won't be added to your Mercurial
repository.

-------
History
-------

hgsvn 0.1.9
-----------

Improvements:

* Improved handling of files containing @ sign in filename (issue52).

* ``hgimportsvn --branch=myname`` imports the SVN repository to a
  named Mercurial branch other than 'default' (patch by Matthias
  Benkmann).

* ``hgpullsvn --svn-retry`` retries to retrieve information on flaky
  connections (patch by Stefanus Du Toit).

* Restrict internal SVN update when running ``hgpushsvn`` to last
  pushed revision (issue79, by ankon).

* Improved syncing of empty directories (issue77, by ankon, reported
  by billmichell).

* ``hgpushsvn --keep-author`` keeps author given in hg log when
  committing to SVN (by wwwjfy).

* Mercurial 1.7 compatibility (issue91, by easye).


hgsvn 0.1.8
-----------

Improvements:

* Convert a local SVN checkout into a hgsvn controlled Mercurial
  repository with ``hgimportsvn --local-only``. No network access is
  needed when setting this flag (aka airplane mode). The Mercurial
  history then starts with the current revision of the SVN
  checkout. Patch by Matt Fowles.

* Commit messages when pushing back to SVN can be edited before
  committing using the -e/--edit command line flag. Issue #29, patch
  by eliterr.

* It's now possible to use ``hgsvn`` with the mq extensions. Both
  ``hgpushsvn`` and ``hgpullsvn`` abort with an error message if mq
  patches are applied when running those commands. Issue #43, patch by
  sterin.

Bug fixes:

* Removal of temporary file when pushing new revisions to SVN on
  Windows fixed. Issue 8 reported by Daniel Dabrowski.

* Changed 'hg log' command line arguments that interfered with default
  options in .hgrc file. Issue 12 reported by Simon Percivall, initial
  patch by Joel Rosdahl and issue 16 reported by Wladimir Palant.

* ``hgpushsvn`` is now compatible with Python 2.4.

* If a SVN changeset contains empty changeset comments, ``hgpullsvn``
  has failed. Empty changeset messages are now handled correctly.

* SVN repositories at revision 0 couldn't be imported. Now it's
  possible to import empty SVN repositories with ``hgimportsvn``.
  Issue #13 reported by tiktuk.

* ``hgpushsvn`` failed when a non-empty directory was removed from
  version control. Issue #15 reported by Keith Yang.

* Proper encoding of commit messages on Windows systems. Issue #19
  reported and patch by Chunlin Yao.

* Change svn:executable property on mode changes when pushing back to
  SVN repository. Issue #24 reported by sterin.

* Improved parsing of SVN messages. Issues #27, #14 patch contributed
  by x63.

* ``hgpushsvn`` whiped uncommitted changes in working directory. Issue
  #32 reported by foxcub.

* ``hgpullsvn`` in dry-run-mode displayed latest fetched revision
  too. Issue #35 reported by Dmitriy Morozov.

* New sub-directories are now created properly. Issue #46 reported by
  Matt Fowles.

* Several fixes by IanH: issue #64, #94, #95.


hgsvn 0.1.7
-----------

Improvements:

* ``hgpushsvn`` fully integrated in this version. This command pushes
  local Mercurial commits back to the SVN repository.

* Add a -n/--dry-run flag to ``hgpullsvn`` and ``hgpushsvn`` to list
  incoming and outgoing changes without committing them to the local
  or remote repository.

* Add verbosity levels to all command line scripts. The default
  verbosity level limits the output of ``hgpullsvn`` and ``hgpushsvn``
  to messages that have a certain relevance to the user. Additional
  messages will be shown with the -v/--verbose flag. The --debug flag
  enables the output of debugging messages including shell commands.

Bug fixes:

* Log files from SVN repositories with path-based authentication
  caused ``hgpullsvn`` and ``hgimportsvn`` to fail with an XML parsing
  error. Restricted paths are now silently ignored (issue5, reported
  by Andreas Sliwka).

* Updated the Mercurial-based lock file mechanism introduced in the
  previous release to work with Mercurial >= 1.2.0. The exception
  class was moved in Mercurial 1.2.0 (issue4).

* ``hgpullsvn`` and ``hgpushsvn`` can now be called from any
  sub-directory within the working copy. Both scripts now take care to
  change their working directory to the root of the working copy (issue3).

* ``hgimportsvn`` exits with a error message when the target directory
  is already a Mercurial repository controlled by hgsvn.

* Detect conflicts when running SVN update. To avoid conflicts when
  pulling new SVN revisions, ``hgpullsvn`` checks if the hg repository
  has uncommitted changes before actually pulling new revisions from
  SVN (issue6, reported and initial patch by Robert).

hgsvn 0.1.6
-----------

Improvements:

* Prefix commit messages with [svn r123] (where 123 is the corresponding SVN
  revision number), rather than just [svn]. Also, trim leading whitespace in
  the original commit message, to avoid blank changeset summaries when the
  message begins with a carriage return.

* Introduce a .hgsvn private directory at the top of the working copy. This
  will us to store various things in a common location without polluting the
  base directory.

* Introduce a lock file (named .hgsvn/lock) to disallow running two hgpullsvn
  instances in parallel on the same repository. The locking mechanism is
  imported from mercurial's own mercurial.lock. If the mercurial package is
  not available, a dummy lock is used instead. Initial patch by Ori Peleg.

* Add a --no-hgignore option to hgimportsvn, for situations where the source
  SVN repository already contains a versioned .hgignore file. Patch by
  Ori Peleg.

* hgsvn can now be bundled as standalone executables using py2exe. Patch by
  Paul Moore.

* More descriptive error message when either hg or svn cannot be executed
  (e.g. not installed). Patch by Joonas Paalasmaa.

Bug fixes:

* Very long commit messages (> 16000 characters) are provided to Mercurial
  through a temporary file rather than the command line, which could fail
  on some platforms. The corresponding commit messages were generated by
  svnmerge. Reported by Ralf Schmitt.

* Filenames starting with a hyphen were considered by hg and SVN as
  command-line options. Report and patch by Mirko Friedenhagen.

* If the last hg changeset mapped to more than one SVN revision, trying to
  update again with ``hgpullsvn`` failed.

* A replaced directory can have added and removed files without them being
  mentioned in the SVN log; we must detect those files ourselves.

* More robust atomicity check for (hg commit, hg tag) sequence. Reported by
  Florent Guillaume.

* Fix a bug when comparing local filesystem paths on Windows. We now invoke
  os.path.normcase on both paths before comparing. Reported by Pavol Murin.


hgsvn 0.1.5
-----------

Improvements:

* In the initial import, parse the svn:ignore property and add suggestions to
  the .hgignore file accordingly. These suggestions are commented by default
  because they are based on the latest version of the svn:ignore property and
  could make us miss some files along the SVN history, if enabled blindingly.

Bug fixes:

* Critical fix for Mercurial 0.9.5, which is stricter with named branches.
  This bug made ``hgimportsvn`` fail when cloning from an auto-detected parent
  repository.
* Honor the SVN_ASP_DOT_NET_HACK environment variable when deciding the name
  of private SVN folders (``.svn`` or ``_svn``). Thanks to Anton Daneika for
  the report and the original patch.

Packaging:

* Change setuptools options to solve bdist_rpm bug under Fedora and other
  Linux distributions. Patch by Tim Wegener.

hgsvn 0.1.4
-----------

Improvements:

* Be able to pull dead (removed) SVN branches by introducing a -p (--svn-peg)
  option to specify the SVN "peg revision". The option must be used with both
  hgimportsvn and hgpullsvn. Patch by Cameron Hutchison.

Bug fixes:

* Allow copying directories with non-ASCII names (reported by Andre Klitzing).
* Make rmtree reliable under Windows. Thanks to Mark (mwatts42) for finding
  both the bug and the solution.
* Fix a problem where there is a symbolic link in the SVN repository that
  points to a directory. Patch by Cameron Hutchison.
* ``svn log`` can output invalid XML when a commit message contains control
  characters. Reported by Tim Wegener.

Other:

* License upgraded to GNU GPL v3 (or later).

hgsvn 0.1.3
-----------

Improvements:

* Performance improvement with ``svn log`` command in ``hgpullsvn`` (suggested
  by Mads Kiilerich and Daniel Berlin).
* Less obscure error message when ``svn info`` fails while returning a
  successful return code.
* Two simplistic man pages added.

Bug fixes:

* Windows compatibility fix by Bill Baxter.
* ``hgimportsvn`` failed when used on a whole repository.
* Fix crash on empty commit message (also reported by Neil Martinsen-Burrell
  and Walter Landry).
* Handle file and directory renames properly (reported by Bill Baxter).
* SVN allows copying from a deleted file by having mixed revisions inside the
  working copy at commit time, but Mercurial doesn't accept it (reported by
  Neil Martinsen-Burrell).

hgsvn 0.1.2
-----------

Improvements:

* Automatically generate ``.hgignore`` file. Not only does it produce cleaner
  output for commands like ``hg status``, but it speeds things up as well.
* ``hgpullsvn`` is more robust in the face of errors and user interruptions.
* Try to be Windows-compatible by not using the commands module.
* Remove dependency on the pysvn library; we use the XML output option of SVN
  commands instead.

Bug fixes:

* Fix a bug in parent repository detection.
* Detect the wicked case where the SVN branch has been overwritten with
  contents of another branch (witnessed with Nose trunk and 0.10-dev branch).
  We can't properly handle this situation, so fail with an explicit message.
* ``svn info`` on base repository URL does not always succeed, use the specific
  project URL instead (reported by Larry Hastings).

hgsvn 0.1.1
-----------

Bug fixes:

* pysvn doesn't really ignore externals, so use the command line for
  ``svn update`` instead (otherwise we get failures for obsolete URLs)
* ``.svn`` directories were not always ignored.
* On large repositories, adding more than 32765 files at once failed because
  of too many arguments on the command line.
* On slow SVN servers, the chunked log fetching algorithm ended up asking for
  0 log entries.

hgsvn 0.1
---------

Initial release.


"""

__all__ = []

__author__ = 'Antoine Pitrou, Andi Albrecht'
__license__ = 'GNU General Public License (version 3 or later)'
__versioninfo__ = (0, 1, 9)

base_version = '.'.join(map(str, __versioninfo__))
full_version = base_version
try:
    import pkg_resources
except ImportError:
    pass
else:
    try:
        full_version = pkg_resources.get_distribution("hgsvn").version
    except pkg_resources.DistributionNotFound:
        pass

__version__ = full_version
