from pypy.conftest import gettestobjspace
from py.test import skip

class AppTest_FiniteDomain(object):
    
    def setup_class(cls):
        cls.space = gettestobjspace('logic', usemodules=('_stackless', ))

    def test_instantiate(self):
        fd = FiniteDomain([1, 2, 3])
        assert fd.size() == 3
        assert set(fd.get_values()) == set([1, 2, 3])

    def test_remove_value(self):
        fd = FiniteDomain([1, 2, 3])
        Sync = fd.give_synchronizer()
        def foo(fd):
            fd.remove_value(2)
            assert fd.size() == 2
            assert set(fd.get_values()) == set([1, 3])
        stacklet(foo, fd)
        assert Sync == True
        
    def test_remove_all_values(self):
        fd = FiniteDomain([3])
        # FIXME: check this is a ConsistencyFailure
        raises(Exception, fd.remove_value, 3) 
        
    def test_remove_values(self):
        fd = FiniteDomain([1, 2, 3])
        Sync = fd.give_synchronizer()
        def foo(fd):
            fd.remove_values([1, 2])
            assert fd.size() == 1
            assert set(fd.get_values()) == set([3,])
        stacklet(foo, fd)
        assert Sync == True

    def test_remove_values_empty_list(self):
        fd = FiniteDomain([1, 2, 3])
        Sync = fd.give_synchronizer()
        assert is_free(Sync)
        fd.remove_values([])
        assert fd.size() == 3
        assert is_free(Sync)

    def test_intersection(self):
        """not used for now"""
        fd1 = FiniteDomain([1, 2, 3])
        fd2 = FiniteDomain([2, 3, 4])
        assert intersection(fd1, fd2) == FiniteDomain([2, 3])
        assert intersection(fd2, fd1) == FiniteDomain([3, 2])

