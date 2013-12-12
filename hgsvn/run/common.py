
from hgsvn import base_version, full_version, ui
from hgsvn.common import change_to_rootdir, fixup_hgsvn_dir, get_hgsvn_lock, LockHeld
from hgsvn.errors import HgSVNError

import sys
import os
from optparse import SUPPRESS_HELP


copyright_message = """\
Copyright (C) 2007 Antoine Pitrou.
Copyright (C) 2009 Andi Albrecht.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

Written by Antoine Pitrou and Andi Albrecht.
"""


def run_parser(parser, long_help=""):
    """
    Add common options to an OptionParser instance, and run parsing.

    A hidden option is added to ease man page production with the help2man tool.
    For example, the following produces a (rather terse) man page for hgpullsvn:
    $ help2man -N "hgpullsvn --help2man" -o man1/hgpullsvn.1
    """
    parser.add_option("", "--version", dest="show_version", action="store_true",
        help="show version and exit")
    parser.add_option("", "--help2man", dest="help2man", action="store_true",
        help=SUPPRESS_HELP)
    parser.remove_option("--help")
    parser.add_option("-h", "--help", dest="show_help", action="store_true",
        help="show this help message and exit")
    parser.add_option("-v", "--verbose", dest="verbosity", const=20,
                      default=10, action="store_const",
                      help="enable additional output")
    parser.add_option("--debug", dest="verbosity", const=30,
                      action="store_const",
                      help="enable debugging output")
    options, args = parser.parse_args()
    if options.show_help:
        if options.help2man and long_help:
            print long_help
            print
        parser.print_help()
        sys.exit(0)
    if options.show_version:
        prog_name = os.path.basename(sys.argv[0])
        if options.help2man:
            print prog_name, base_version
            print
            print copyright_message
        else:
            print prog_name, full_version
        sys.exit(0)
    ui.update_config(options)
    return options, args

def display_parser_error(parser, message):
    """
    Display an options error, and terminate.
    """
    print "error:", message
    print
    parser.print_help()
    sys.exit(1)


def locked_main(real_main, *args, **kwds):
    """Wrapper for main() functions, that takes care of .hgsvn/lock."""
    # Make sure that we work in the checkout's top-level directory (issue3).
    try:
        change_to_rootdir()
    except HgSVNError, err:
        sys.stderr.write("%s\n" % err)
        return 1
    # We must do this before trying to take the lock file
    fixup_hgsvn_dir('.')
    try:
        l = get_hgsvn_lock()
    except LockHeld, e:
        print "Aborting:", e
        return 1
    try:
        return real_main(*args, **kwds)
    finally:
        l.release()

