#!/usr/bin/env python

# Setuptools-based setup script
# See:
# - http://peak.telecommunity.com/DevCenter/setuptools (*)
# - http://peak.telecommunity.com/DevCenter/EasyInstall

# (*) QOTD:
# "Notice that after each pre or post-release tag, you are free to place another
# release number, followed again by more pre- or post-release tags. For example,
# 0.6a9.dev-r41475 could denote Subversion revision 41475 of the in- development
# version of the ninth alpha of release 0.6. Notice that dev is a pre-release tag,
# so this version is a lower version number than 0.6a9, which would be the actual
# ninth alpha of release 0.6. But the -r41475 is a post-release tag, so this
# version is newer than 0.6a9.dev."

from ez_setup import use_setuptools
use_setuptools(download_delay=3)
from setuptools import setup, find_packages

from hgsvn import base_version, __doc__ as long_description

commands = ['hgimportsvn', 'hgpullsvn', 'hgpushsvn']

install_requires = []
try:
    from xml.etree import ElementTree
except ImportError:
    try:
        import elementtree
    except ImportError:
        install_requires = ['elementtree']

extra_cmds = {}
try:
    import py2exe
    import sys

    # ModuleFinder can't handle runtime changes to __path__, but win32com uses
    # them, particularly for people who build from sources.  Hook this in.
    import modulefinder
    import win32com
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    __import__("win32com.shell")
    m = sys.modules["win32com.shell"]
    for p in m.__path__[1:]:
        modulefinder.AddPackagePath("win32com.shell", p)

    extra_cmds['console'] = ["hgimportsvn.py", "hgpullsvn.py",
                             "hgpushsvn.py"]
    extra_cmds['zipfile'] = "hgsvnlib.zip"
except ImportError:
    pass

setup(
    name = "hgsvn",
    author = 'Antoine Pitrou',
    author_email = 'antoine@pitrou.net',
    description = ("A set of scripts to work locally on Subversion checkouts "
        "using Mercurial"
    ),
    long_description = long_description,
    license = 'GNU GPL',
    url = 'http://bitbucket.org/andialbrecht/hgsvn',

    # *Next* version, not previous!
    version = base_version,
    packages = find_packages(exclude=["ez_setup"]),

    test_suite = "nose.collector",

    install_requires = install_requires,

    entry_points = {
        'console_scripts': [
            '%s = hgsvn.run.%s:main' % (s, s) for s in commands
        ],
    },

    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Version Control',
    ],
    options=dict(py2exe=dict(bundle_files=1)),
    **extra_cmds
)
