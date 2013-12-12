import locale
import os
import shutil
import subprocess
import tempfile
import unittest

from hgsvn.run import hgpushsvn


class RepoTest(unittest.TestCase):

    def _run_cmd(self, cmd_args):
        p = subprocess.Popen(cmd_args)
        p.wait()

    def _write_file(self, fname, content, commit=False, added=False,
                    msg='test'):
        f = open(os.path.join(self.repo_dir, fname), 'w')
        f.write(content)
        f.close()
        if added:
            self._run_cmd(['hg', 'add', fname])
        if commit:
            self._run_cmd(['hg', 'commit', '-m', msg])

    def _remove_file(self, fname, commit=False):
        self._run_cmd(['hg', 'rm', fname])
        if commit:
            self._run_cmd(['hg', 'commit', '-m', 'test'])

    def _move_file(self, source, dest, commit=False):
        self._run_cmd(['hg', 'mv', source, dest])
        if commit:
            self._run_cmd(['hg', 'commit', '-m',
                           '"Copied %s -> %s"' % (source, dest)])

    def setUp(self):
        self.repo_dir = tempfile.mkdtemp()
        self._currdir = os.getcwd()
        os.chdir(self.repo_dir)
        self._run_cmd(['hg', 'init'])
        self.test_file = os.path.join(self.repo_dir, 'foo')
        f = open(self.test_file, 'w')
        f.write('foo')
        f.close()
        self._run_cmd(['hg', 'add', 'foo'])
        self._run_cmd(['hg', 'commit', '-m', '"Initial."'])

    def tearDown(self):
        shutil.rmtree(self.repo_dir)
        os.chdir(self._currdir)


class TestHgClient(RepoTest):

    def test_get_hg_cset(self):
        ret = hgpushsvn.get_hg_cset('tip')
        self.assert_(isinstance(ret, basestring))
        self.assertEqual(ret, ret.strip())
        self.assertEqual(ret.count(':'), 1)
        first, last = ret.split(':')
        self.assert_(first.isdigit())
        self.assert_(last.isalnum())

    def test_strip_hg_rev(self):
        self.assertEqual(hgpushsvn.strip_hg_rev('1:2'), '2')
        self.assertEqual(hgpushsvn.strip_hg_rev('1:2\n'), '2')

    def test_get_hg_changes(self):
        ret = hgpushsvn.get_hg_changes('tip')
        self.assert_(isinstance(ret, tuple))
        self.assertEqual(len(ret), 4)
        added, removed, modified, copied = ret
        self.assert_(isinstance(added, list))
        self.assert_(isinstance(removed, list))
        self.assert_(isinstance(modified, list))
        self.assert_(isinstance(copied, dict))
        self.assertEqual(len(added), 0)
        self.assertEqual(len(removed), 0)
        self.assertEqual(len(modified), 0)
        self.assertEqual(len(copied), 0)
        rev1 = hgpushsvn.strip_hg_rev(hgpushsvn.get_hg_cset('tip'))
        self._write_file('foo', 'bar')
        self._write_file('bar', 'foo', commit=True, added=True)
        rev2 = hgpushsvn.strip_hg_rev(hgpushsvn.get_hg_cset('tip'))
        ret = hgpushsvn.get_hg_changes('%s:%s' % (rev1, rev2))
        self.assert_(isinstance(ret, tuple))
        self.assertEqual(len(ret), 4)
        added, removed, modified, copied = ret
        self.assert_(isinstance(added, list))
        self.assert_(isinstance(removed, list))
        self.assert_(isinstance(modified, list))
        self.assertEqual(len(added), 1)
        self.assertEqual(len(removed), 0)
        self.assertEqual(len(modified), 1)
        rev1 = rev2
        self._remove_file('bar', commit=True)
        rev2 = hgpushsvn.strip_hg_rev(hgpushsvn.get_hg_cset('tip'))
        ret = hgpushsvn.get_hg_changes('%s:%s' % (rev1, rev2))
        self.assert_(isinstance(ret, tuple))
        self.assertEqual(len(ret), 4)
        added, removed, modified, copied = ret
        self.assert_(isinstance(added, list))
        self.assert_(isinstance(removed, list))
        self.assert_(isinstance(modified, list))
        self.assertEqual(len(added), 0)
        self.assertEqual(len(removed), 1)
        self.assertEqual(len(modified), 0)

    def test_moved_file(self):
        self._move_file('foo', 'bar')
        ret = hgpushsvn.get_hg_changes('tip')
        self.assert_(isinstance(ret, tuple))
        self.assertEqual(len(ret), 4)
        added, removed, modified, copied = ret
        self.assertEqual(len(copied), 1)
        self.assertEqual(len(modified), 0)
        self.assertEqual(len(added), 0)
        self.assertEqual(len(removed), 1)

    def test_get_hg_revs(self):
        rev = hgpushsvn.strip_hg_rev(hgpushsvn.get_hg_cset('tip'))
        self._write_file('foo', 'bar', commit=True)
        rev2 = hgpushsvn.strip_hg_rev(hgpushsvn.get_hg_cset('tip'))
        revs = hgpushsvn.get_hg_revs(rev, 'default')
        self.assert_(isinstance(revs, list))
        self.assertEqual(len(revs), 2)
        self.assertEqual(revs[0], rev)
        self.assertEqual(revs[1], rev2)
        self._write_file('foo', 'bar2', commit=True)
        revs = hgpushsvn.get_hg_revs(rev, 'default')
        self.assert_(isinstance(revs, list))
        self.assertEqual(len(revs), 3)
        self.assertEqual(revs[0], rev)
        self.assertEqual(revs[1], rev2)
        # Change test file in different branch
        self._run_cmd(['hg', 'branch', 'testing'])
        self._write_file('foo', 'bar3', commit=True)
        revs = hgpushsvn.get_hg_revs(rev, 'default')
        self.assert_(isinstance(revs, list))
        self.assertEqual(len(revs), 3)
        self.assertEqual(revs[0], rev)
        self.assertEqual(revs[1], rev2)

    def test_get_hg_cset_description(self):
        self._write_file('foo', 'bar', commit=True, msg='123')
        rev_raw = hgpushsvn.get_hg_cset('tip')
        rev = hgpushsvn.strip_hg_rev(rev_raw)
        ret = hgpushsvn.get_hg_cset_description(rev)
        self.assert_(isinstance(ret, basestring))
        self.assertEqual(ret, '123')
        self._write_file('foo', 'bar', commit=True, msg=' 123\n')
        rev_raw = hgpushsvn.get_hg_cset('tip')
        rev = hgpushsvn.strip_hg_rev(rev_raw)
        ret = hgpushsvn.get_hg_cset_description(rev)
        self.assert_(isinstance(ret, basestring))
        self.assertEqual(ret, '123')


