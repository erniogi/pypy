import py
import sys
from pypy.conftest import gettestobjspace

class TestImport:
    def test_simple(self):
        from pypy.module._multiprocessing import interp_connection
        from pypy.module._multiprocessing import interp_semaphore

class BaseConnectionTest(object):
    def test_connection(self):
        rhandle, whandle = self.make_pair()

        obj = [1, 2.0, "hello"]
        whandle.send(obj)
        obj2 = rhandle.recv()
        assert obj == obj2

class AppTestWinpipeConnection(BaseConnectionTest):
    def setup_class(cls):
        if sys.platform != "win32":
            py.test.skip("win32 only")

        space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
        cls.space = space

        # stubs for some modules,
        # just for multiprocessing to import correctly on Windows
        w_modules = space.sys.get('modules')
        space.setitem(w_modules, space.wrap('msvcrt'), space.sys)
        space.setitem(w_modules, space.wrap('_subprocess'), space.sys)

        cls.w_make_pair = space.appexec([], """():
            import multiprocessing
            def make_pair():
                rhandle, whandle = multiprocessing.Pipe()
                return rhandle, whandle
            return make_pair
        """)

class AppTestSocketConnection(BaseConnectionTest):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
        cls.space = space
        cls.w_make_pair = space.appexec([], """():
            import _multiprocessing
            import os
            def make_pair():
                fd1, fd2 = os.pipe()
                rhandle = _multiprocessing.Connection(fd1, writable=False)
                whandle = _multiprocessing.Connection(fd2, readable=False)
                return rhandle, whandle
            return make_pair
        """)
