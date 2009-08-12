
from pypy.rpython.ootypesystem import ootype
from pypy.translator.oosupport.metavm import MicroInstruction
from pypy.translator.avm.avm1gen import StackDummy

class _SetField(MicroInstruction):
    def render(self, generator, op):
        this, field, value = op.args

        if value.concretetype is ootype.Void:
            return
        
        generator.load(this)
        generator.load(field)
        generator.load(value)
        generator.set_member()

class _GetField(MicroInstruction):
    def render(self, generator, op):
        
        if op.result.concretetype is ootype.Void:
            return
        
        this, field = op.args
        generator.load(this)
        generator.load(field)
        generator.get_member()

class _StoreResultStart(MicroInstruction):
    def render(self, generator, op):
        print "STORERESULT START:", op.result.name
        generator.push_const(op.result.name)

class _StoreResultEnd(MicroInstruction):
    def render(self, generator, op):
        print "STORERESULT END:", op.result.name
        generator.set_variable()


class _PushArgsForFunctionCall(MicroInstruction):
    def render(self, generator, op):
        args = op.args
        for arg in args:
            print arg, type(arg)
            generator.load(arg)
        generator.push_const(len(args))

class CallConstantMethod(MicroInstruction):
    def __init__(self, obj, func_name):
        self.obj = obj
        self.func_name = func_name

    def render(self, generator, op):
        generator.push_var(self.obj)
        generator.call_method_n(self.func_name)

class PushConst(MicroInstruction):
    def __init__(self, *args):
        self.args = args
        
    def render(self, generator, op):
        generator.push_const(*self.args)

PushArgsForFunctionCall = _PushArgsForFunctionCall()
StoreResultStart        = _StoreResultStart()
StoreResultEnd          = _StoreResultEnd()
GetField                = _GetField()
SetField                = _SetField()
