
import autopath
import py
from pypy.annotation.model import *
from pypy.annotation.listdef import ListDef, MOST_GENERAL_LISTDEF


listdef1 = ListDef(None, SomeTuple([SomeInteger(nonneg=True), SomeString()]))
listdef2 = ListDef(None, SomeTuple([SomeInteger(nonneg=False), SomeString()]))

s1 = SomeObject()
s2 = SomeInteger(nonneg=True)
s3 = SomeInteger(nonneg=False)
s4 = SomeList(listdef1)
s5 = SomeList(listdef2)
s6 = SomeImpossibleValue()
slist = [s1,s2,s3,s4,s6]  # not s5 -- unionof(s4,s5) modifies s4 and s5


class C(object):
    pass

class DummyClassDef:
    def __init__(self, cls=C):
        self.cls = cls

si0 = SomeInstance(DummyClassDef(), True)
si1 = SomeInstance(DummyClassDef())
sNone = SomePBC({None: True})
sTrue = SomeBool()
sTrue.const = True
sFalse = SomeBool()
sFalse.const = False

def test_is_None():
    assert pair(sNone, sNone).is_() == sTrue
    assert pair(si1, sNone).is_() == sFalse
    assert pair(si0, sNone).is_() != sTrue
    assert pair(si0, sNone).is_() != sFalse
    assert pair(si0, sNone).is_() == SomeBool()

def test_equality():
    assert s1 != s2 != s3 != s4 != s5 != s6
    assert s1 == SomeObject()
    assert s2 == SomeInteger(nonneg=True)
    assert s3 == SomeInteger(nonneg=False)
    assert s4 == SomeList(listdef1)
    assert s5 == SomeList(listdef2)
    assert s6 == SomeImpossibleValue()

def test_contains():
    assert ([(s,t) for s in slist for t in slist if s.contains(t)] ==
            [(s1,s1), (s1,s2), (s1,s3), (s1,s4), (s1,s6),
                      (s2,s2),                   (s2,s6),
                      (s3,s2), (s3,s3),          (s3,s6),
                                        (s4,s4), (s4,s6),
                                                 (s6,s6)])

def test_union():
    assert ([unionof(s,t) for s in slist for t in slist] ==
            [s1, s1, s1, s1, s1,
             s1, s2, s3, s1, s2,
             s1, s3, s3, s1, s3,
             s1, s1, s1, s4, s4,
             s1, s2, s3, s4, s6])

def test_commonbase_simple():
    class A0: 
        pass
    class A1(A0): 
        pass
    class A2(A0): 
        pass
    class B1(object):
        pass
    class B2(object):
        pass
    class B3(object, A0):
        pass
    assert commonbase(A1,A2) is A0 
    assert commonbase(A1,A0) is A0
    assert commonbase(A1,A1) is A1
    assert commonbase(A2,B2) is object 
    assert commonbase(A2,B3) is A0

def test_list_union():
    listdef1 = ListDef(None, SomeInteger(nonneg=True))
    listdef2 = ListDef(None, SomeInteger(nonneg=False))
    s1 = SomeList(listdef1)
    s2 = SomeList(listdef2)
    assert s1 != s2
    s3 = unionof(s1, s2)
    assert s1 == s2 == s3

def test_list_contains():
    listdef1 = ListDef(None, SomeInteger(nonneg=True))
    s1 = SomeList(listdef1)
    s2 = SomeList(MOST_GENERAL_LISTDEF)
    assert s1 != s2
    assert s2.contains(s1)
    assert s1 != s2
    assert not s1.contains(s2)
    assert s1 != s2

def test_ll_to_annotation():
    s_z = ll_to_annotation(lltype.Signed._defl())
    s_s = SomeInteger()
    s_u = SomeInteger(nonneg=True, unsigned=True)
    assert s_z.contains(s_s)
    assert not s_z.contains(s_u)
    s_uz = ll_to_annotation(lltype.Unsigned._defl())
    assert s_uz.contains(s_u)
    assert ll_to_annotation(lltype.Bool._defl()).contains(SomeBool())
    assert ll_to_annotation(lltype.Char._defl()).contains(SomeChar())
    S = lltype.GcStruct('s')
    A = lltype.GcArray()
    s_p = ll_to_annotation(lltype.malloc(S))
    assert isinstance(s_p, SomePtr) and s_p.ll_ptrtype == lltype.Ptr(S)
    s_p = ll_to_annotation(lltype.malloc(A, 0))
    assert isinstance(s_p, SomePtr) and s_p.ll_ptrtype == lltype.Ptr(A)
    C = ootype.Class('C', None, {})
    s_p = ll_to_annotation(ootype.new(C))
    assert isinstance(s_p, SomeRef) and s_p.ootype == C

def test_annotation_to_lltype():
    from pypy.rpython.rarithmetic import r_uint
    s_i = SomeInteger()
    s_pos = SomeInteger(nonneg=True)
    s_1 = SomeInteger(nonneg=True); s_1.const = 1
    s_m1 = SomeInteger(nonneg=False); s_m1.const = -1
    s_u = SomeInteger(nonneg=True, unsigned=True); 
    s_u1 = SomeInteger(nonneg=True, unsigned=True); 
    s_u1.const = r_uint(1)
    assert annotation_to_lltype(s_i) == lltype.Signed
    assert annotation_to_lltype(s_pos) == lltype.Signed
    assert annotation_to_lltype(s_1) == lltype.Signed
    assert annotation_to_lltype(s_m1) == lltype.Signed
    assert annotation_to_lltype(s_u) == lltype.Unsigned
    assert annotation_to_lltype(s_u1) == lltype.Unsigned
    assert annotation_to_lltype(SomeBool()) == lltype.Bool
    assert annotation_to_lltype(SomeChar()) == lltype.Char
    PS = lltype.Ptr(lltype.GcStruct('s'))
    s_p = SomePtr(ll_ptrtype=PS)
    assert annotation_to_lltype(s_p) == PS
    py.test.raises(ValueError, "annotation_to_lltype(si0)")
    C = ootype.Class('C', None, {})
    ref = SomeRef(C)
    assert annotation_to_lltype(ref) == C
    
def test_ll_union():
    PS1 = lltype.Ptr(lltype.GcStruct('s'))
    PS2 = lltype.Ptr(lltype.GcStruct('s'))
    PS3 = lltype.Ptr(lltype.GcStruct('s3'))
    PA1 = lltype.Ptr(lltype.GcArray())
    PA2 = lltype.Ptr(lltype.GcArray())

    assert unionof(SomePtr(PS1),SomePtr(PS1)) == SomePtr(PS1)
    assert unionof(SomePtr(PS1),SomePtr(PS2)) == SomePtr(PS2)
    assert unionof(SomePtr(PS1),SomePtr(PS2)) == SomePtr(PS1)

    assert unionof(SomePtr(PA1),SomePtr(PA1)) == SomePtr(PA1)
    assert unionof(SomePtr(PA1),SomePtr(PA2)) == SomePtr(PA2)
    assert unionof(SomePtr(PA1),SomePtr(PA2)) == SomePtr(PA1)

    assert unionof(SomePtr(PS1),SomeImpossibleValue()) == SomePtr(PS1)
    assert unionof(SomeImpossibleValue(), SomePtr(PS1)) == SomePtr(PS1)

    py.test.raises(AssertionError, "unionof(SomePtr(PA1), SomePtr(PS1))")
    py.test.raises(AssertionError, "unionof(SomePtr(PS1), SomePtr(PS3))")
    py.test.raises(AssertionError, "unionof(SomePtr(PS1), SomeInteger())")
    py.test.raises(AssertionError, "unionof(SomePtr(PS1), SomeObject())")
    py.test.raises(AssertionError, "unionof(SomeInteger(), SomePtr(PS1))")
    py.test.raises(AssertionError, "unionof(SomeObject(), SomePtr(PS1))")

def test_oo_union():
    C1 = ootype.Class("C1", None)
    C2 = ootype.Class("C2", C1)
    C3 = ootype.Class("C3", C1)
    D = ootype.Class("D", None)
    assert unionof(SomeRef(C1), SomeRef(C1)) == SomeRef(C1)
    assert unionof(SomeRef(C1), SomeRef(C2)) == SomeRef(C1)
    assert unionof(SomeRef(C2), SomeRef(C1)) == SomeRef(C1)
    assert unionof(SomeRef(C2), SomeRef(C3)) == SomeRef(C1)

    assert unionof(SomeRef(C1),SomeImpossibleValue()) == SomeRef(C1)
    assert unionof(SomeImpossibleValue(), SomeRef(C1)) == SomeRef(C1)

    py.test.raises(AssertionError, "unionof(SomeRef(C1), SomeRef(D))")
    py.test.raises(AssertionError, "unionof(SomeRef(D), SomeRef(C1))")
    py.test.raises(AssertionError, "unionof(SomeRef(C1), SomeInteger())")
    py.test.raises(AssertionError, "unionof(SomeInteger(), SomeRef(C1))")
    py.test.raises(AssertionError, "unionof(SomeRef(C1), SomeObject())")
    py.test.raises(AssertionError, "unionof(SomeObject(), SomeRef(C1))")

if __name__ == '__main__':
    for name, value in globals().items():
        if name.startswith('test_'):
            value()

