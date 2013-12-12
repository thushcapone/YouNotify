import os
import shutil
import tempfile

from _test import *

from hgsvn import common


class TestCommands(object):
    def test_hg(self):
        s = common.run_hg(['version', '-q'])
        s = s.split()[0]
        eq_(s.lower(), 'mercurial')

    def test_svn(self):
        s = common.run_svn(['--version', '-q'])
        eq_(s.split('.')[0], '1')

class CommandsBase(object):
    def test_echo(self):
        echo_string = 'foo'
        s = self.command_func('echo', [echo_string])
        eq_(s.rstrip(), echo_string)

    def test_echo_with_escapes(self):
        echo_string = 'foo \n"\' baz'
        s = self.command_func('echo', [echo_string])
        eq_(s.rstrip(), echo_string)

    def test_bulk_args(self):
        sep = '-'
        args = ['a', 'b', 'c']
        n_args = len(args)
        bulk_args = ['%d' % i for i in xrange(3000)]
        out = self.command_func('echo', [sep] + args, bulk_args)
        sub_results = out.split(sep)
        eq_(sub_results.pop(0).strip(), "")
        bulk_pos = 0
        for s in sub_results:
            l = s.split()
            eq_(l[:n_args], args)
            n_bulk = len(l) - n_args
            assert n_bulk < 256
            eq_(l[n_args:], bulk_args[bulk_pos:bulk_pos + n_bulk])
            bulk_pos += n_bulk
        eq_(bulk_pos, len(bulk_args))


class TestShellCommands(CommandsBase):
    command_func = staticmethod(common.run_shell_command)

class TestNonShellCommands(CommandsBase):
    command_func = staticmethod(common.run_command)


class TestLock(object):

    test_mercurial = True

    def setUp(self):
        if self.test_mercurial:
            try:
                from mercurial.lock import lock
            except ImportError:
                raise SkipTest  # mercurial not installed
        self._test_base = tempfile.mkdtemp()
        common.fixup_hgsvn_dir(self._test_base)

    def tearDown(self):
        shutil.rmtree(self._test_base)

    def test_lock_set_release(self):
        def lock_exists():
            private_dir = os.path.join(self._test_base,
                                       common.hgsvn_private_dir)
            return common.hgsvn_lock_file in os.listdir(private_dir)

        l = common.get_hgsvn_lock(self._test_base)
        lock_file = os.path.join(self._test_base, common.hgsvn_private_dir,
                                 common.hgsvn_lock_file)
        assert_true(lock_exists())
        l.release()
        assert_false(lock_exists())

    def test_locked(self):
        l = common.get_hgsvn_lock(self._test_base)
        assert_raises(common.LockHeld,
                      common.get_hgsvn_lock, self._test_base)
        l.release()



class TestSimpleFileLock(TestLock):

    test_mercurial = False

    def setUp(self):
        self._real_lock = common._lock
        self._real_lock_held = common.LockHeld
        common._lock = common._SimpleFileLock
        common.LockHeld = common._LockHeld
        super(TestSimpleFileLock, self).setUp()

    def tearDown(self):
        super(TestSimpleFileLock, self).tearDown()
        common._lock = self._real_lock
        common.LockHeld = self._real_lock_held


class TestSwitchBranch(object):

    def setUp(self):
        self._wd = tempfile.mkdtemp()
        self._cwd = os.getcwd()
        os.chdir(self._wd)
        common.run_hg(["init"])
        f = open("foo", "w")
        f.write("foo")
        f.close()
        common.run_hg(["add", "foo"])
        common.run_hg(["commit", "-m", "Initial"])

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self._wd)

    def test_switch_clean_repo(self):
        common.run_hg(["branch", "test"])
        f = open("bar", "w")
        f.write("bar")
        f.close()
        common.run_hg(["add", "bar"])
        common.run_hg(["commit", "-m", '"bar added."'])
        eq_(True, common.hg_switch_branch("test", "default"))

    def test_switch_dirty_repo(self):
        common.run_hg(["branch", "test"])
        f = open("bar", "w")
        f.write("bar")
        f.close()
        common.run_hg(["add", "bar"])
        eq_(False, common.hg_switch_branch("test", "default"))

class TestOnceOrMore(object):
    def setUp(self):
        self._counter = 0

    def increment(self, count):
        self._counter += count
        return self._counter

    def increment_until_3(self, count):
        self.increment(count)
        if self._counter < 3:
            raise Exception("Counter not high enough yet")

    def test_no_exception(self):
        foo = common.once_or_more("Foo", False, self.increment, 1)
        eq_(1, self._counter)
        eq_(1, foo)
        foo = common.once_or_more("Foo", True, self.increment, 2)
        eq_(3, self._counter)
        eq_(3, foo)

    @raises(Exception)
    def test_with_exception_no_retry(self):
        eq_(0, self._counter)
        common.once_or_more("Foo", False, self.increment_until_3, 1)

    def test_with_exception_retry(self):
        eq_(0, self._counter)
        common.once_or_more("Foo", True, self.increment_until_3, 1)
        eq_(3, self._counter)
    
        
            


        
