
from _test import *

from hgsvn import svnclient

import time


def eq_utc_timestamp(timestamp, time_tuple):
    eq_(time.gmtime(timestamp)[:6], time_tuple)


class TestSVNDate(object):
    """
    Tests for SVN date handling.
    """

    def test_parse(self):
        """
        Parsing SVN dates.
        """
        svn_date = "2007-05-01T18:33:32.749605Z"
        timestamp = svnclient.svn_date_to_timestamp(svn_date)
        eq_(timestamp, 1178044412)
        eq_utc_timestamp(timestamp, (2007, 5, 1, 18, 33, 32))


svn_info_xml = """<?xml version="1.0"?>
<info>
<entry
   kind="dir"
   path="trunk"
   revision="20191">
<url>svn://svn.twistedmatrix.com/svn/Twisted/trunk</url>
<repository>
<root>svn://svn.twistedmatrix.com/svn/Twisted</root>
<uuid>bbbe8e31-12d6-0310-92fd-ac37d47ddeeb</uuid>
</repository>
<commit
   revision="20185">
<author>ralphm</author>
<date>2007-05-04T10:47:32.843908Z</date>
</commit>
</entry>
</info>"""

svn_info_xml_rev0 = """<?xml version="1.0"?>
<info>
<entry
   kind="dir"
   path="testsvn"
   revision="0">
<url>file:///home/foo/bar</url>
<repository>
<root>file:///home/foo/bar</root>
<uuid>936c9acc-016e-4cc8-a158-a434ae94e2dd</uuid>
</repository>
<commit
   revision="0">
<date>2009-09-17T19:21:13.394243Z</date>
</commit>
</entry>
</info>"""

class TestSVNInfo(object):
    """
    Tests for handling SVN wc/repo information.
    """

    def test_parse(self):
        """
        Parsing the output of 'svn info --xml'.
        """
        d = svnclient.parse_svn_info_xml(svn_info_xml)
        eq_(d['url'], 'svn://svn.twistedmatrix.com/svn/Twisted/trunk')
        eq_(d['repos_url'], 'svn://svn.twistedmatrix.com/svn/Twisted')
        eq_(d['revision'], 20191)
        eq_(d['last_changed_rev'], 20185)

    def test_parse_rev0(self):
        """
        Parsing the output of 'svn info --xml' for revision 0.
        """
        d = svnclient.parse_svn_info_xml(svn_info_xml_rev0)
        eq_(d['url'], 'file:///home/foo/bar')
        eq_(d['repos_url'], 'file:///home/foo/bar')
        eq_(d['revision'], 0)


svn_log_xml = """<?xml version="1.0"?>
<log>
<logentry
   revision="1777">
<author>apitrou</author>
<date>2007-03-29T09:37:56.023608Z</date>
<paths>
<path
   copyfrom-path="/scripts"
   copyfrom-rev="1776"
   action="A">/hgsvn</path>
<path
   action="D">/scripts</path>
</paths>
<msg>move dir to better-named location

</msg>
</logentry>
<logentry
   revision="1776">
<author>apitrou</author>
<date>2007-03-28T16:51:15.339713Z</date>
<paths>
<path
   action="M">/scripts/hgimportsvn.py</path>
</paths>
<msg>automatically detect a parent hg repo tracking the parent SVN branch,
and pull from it.

</msg>
</logentry>
</log>"""

svn_log_xml_with_empty_msg = """<?xml version="1.0"?>
<log>
<logentry
   revision="1776">
<author>apitrou</author>
<date>2007-03-28T16:51:15.339713Z</date>
<paths>
<path
   action="M">/scripts/hgimportsvn.py</path>
</paths>
<msg></msg>
</logentry>
</log>"""

svn_log_xml_with_invalid_chars = ('<?xml version="1.0"?>'
    + '\n<log>\n<logentry\n   revision="1722">\n<author>synic</author>\n'
    + '<date>2006-11-08T19:56:30.120180Z</date>\n'
    + '<msg>fixed some plugin bugs===+=\x1f\x1f\x1f---\n</msg>\n</logentry>\n</log>\n')

svn_log_xml_with_path_restricted = """<?xml version="1.0"?>
<log>
<logentry
   revision="3">
</logentry>
<logentry
   revision="2">
<author>aalbrecht</author>
<date>2009-06-22T05:53:13.019086Z</date>
<msg>Added bar.</msg>
</logentry>
<logentry
   revision="1">
<author>aalbrecht</author>
<date>2009-06-22T05:52:54.418773Z</date>
<msg>Initial layout.</msg>
</logentry>
</log>
"""


class TestSVNLog(object):
    """
    Tests for handling SVN logs.
    """

    def test_parse(self):
        """
        Parsing an SVN log in XML format.
        """
        entries = svnclient.parse_svn_log_xml(svn_log_xml)
        eq_(len(entries), 2)
        e = entries[0]
        eq_(e['author'], 'apitrou')
        eq_(e['revision'], 1777)
        eq_utc_timestamp(e['date'], (2007, 3, 29, 9, 37, 56))
        eq_(e['message'], "move dir to better-named location\n\n")
        paths = e['changed_paths']
        eq_(len(paths), 2)
        p = paths[0]
        eq_(p, {
            'path': '/hgsvn',
            'action': 'A',
            'copyfrom_path': '/scripts',
            'copyfrom_revision': 1776,
        })
        p = paths[1]
        eq_(p, {
            'path': '/scripts',
            'action': 'D',
            'copyfrom_path': None,
            'copyfrom_revision': None,
        })
        e = entries[1]
        eq_(e['author'], 'apitrou')
        eq_(e['revision'], 1776)
        eq_utc_timestamp(e['date'], (2007, 3, 28, 16, 51, 15))
        eq_(len(e['changed_paths']), 1)

    def test_parse_with_empty_msg(self):
        """
        Parsing an SVN log entry with an empty commit message.
        """
        entries = svnclient.parse_svn_log_xml(svn_log_xml_with_empty_msg)
        eq_(len(entries), 1)
        e = entries[0]
        eq_(e['message'], "")

    def test_parse_with_invalid_xml(self):
        """
        Parsing an SVN log entry with invalid XML characters.
        """
        entries = svnclient.parse_svn_log_xml(svn_log_xml_with_invalid_chars)
        eq_(len(entries), 1)
        msg = entries[0]['message']
        assert msg.startswith('fixed some plugin bugs===+=')
        assert msg.strip().endswith('---')

    def test_parse_with_path_based_restrictions(self):
        # Stub log entries appear when there is path-based authentication
        # enabled on specific directories.
        entries = svnclient.parse_svn_log_xml(svn_log_xml_with_path_restricted)
        eq_(len(entries), 3)
        msg = entries[1]['message']
        assert msg.startswith('Added bar.')
        keys = ('revision', 'author', 'date', 'message', 'changed_paths')
        eq_(set(keys), set(entries[0]))
        eq_([], entries[0]['changed_paths'])


svn_status_xml = """<?xml version="1.0"?>
<status>
<entry
   path="_doc.html">
<wc-status
   props="none"
   item="unversioned">
</wc-status>
</entry>
<entry
   path="ez_setup">
<wc-status
   props="none"
   item="external">
</wc-status>
</entry>
<entry
   path="hgcreatesvn.py">
<wc-status
   props="normal"
   item="normal"
   revision="1962">
<commit
   revision="1774">
<author>apitrou</author>
<date>2007-03-28T15:22:22.975800Z</date>
</commit>
</wc-status>
</entry>
<entry
   path="hgsvn/svnclient.py">
<wc-status
   props="none"
   item="modified"
   revision="1962">
<commit
   revision="1962">
<author>apitrou</author>
<date>2007-05-04T19:59:06.567367Z</date>
</commit>
</wc-status>
</entry>
</status>"""

svn_status_xml_with_base_dir = """<?xml version="1.0"?>
<status>
<target
   path="/home/antoine/hgsvn">
<entry
   path="/home/antoine/hgsvn/build">
<wc-status
   props="none"
   item="unversioned">
</wc-status>
</entry>
</target>
</status>"""

class TestSVNStatus(object):
    """
    Tests for handling status of an SVN working copy.
    """

    def test_parse(self):
        """
        Parsing the output of 'svn st --xml'.
        """
        entries = svnclient.parse_svn_status_xml(svn_status_xml)
        eq_(len(entries), 4)
        e = entries[0]
        eq_(e['path'], '_doc.html')
        eq_(e['type'], 'unversioned')
        e = entries[1]
        eq_(e['path'], 'ez_setup')
        eq_(e['type'], 'external')
        e = entries[2]
        eq_(e['path'], 'hgcreatesvn.py')
        eq_(e['type'], 'normal')
        e = entries[3]
        eq_(e['path'], 'hgsvn/svnclient.py')
        eq_(e['type'], 'normal')

    def test_parse_with_base_dir(self):
        """
        Parsing the output of 'svn st --xml' with an explicit base dir.
        """
        entries = svnclient.parse_svn_status_xml(
            svn_status_xml_with_base_dir, '/home/antoine/hgsvn')
        eq_(len(entries), 1)
        e = entries[0]
        eq_(e['path'], 'build')
        eq_(e['type'], 'unversioned')


def test_get_svn_client_version():
    version = svnclient.get_svn_client_version()
    assert_true(isinstance(version, tuple))
    assert_true(len(version) >= 2)
    for part in version:
        assert_true(isinstance(part, int))
    eq_(version[0], 1)
