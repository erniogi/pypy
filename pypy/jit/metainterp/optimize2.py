
""" Simplified optimize.py
"""
from pypy.jit.metainterp.resoperation import rop, ResOperation, opname
from pypy.jit.metainterp.history import Const, Box

class VirtualizedListAccessedWithVariableArg(Exception):
    pass

class InstanceNode(object):
    def __init__(self, source, const=False):
        self.source = source
        if const:
            assert isinstance(source, Const)
        self.const = const
        self.cls = None
        self.cleanfields = {}
        self.dirtyfields = {}
        self.virtualized = False
        self.possibly_virtualized_list = False

    def __repr__(self):
        flags = ''
        #if self.escaped:           flags += 'e'
        #if self.startbox:          flags += 's'
        if self.const:             flags += 'c'
        #if self.virtual:           flags += 'v'
        if self.virtualized:       flags += 'V'
        return "<InstanceNode %s (%s)>" % (self.source, flags)

class Specializer(object):
    loop = None
    nodes = None

    def __init__(self, opts):
        # NOT_RPYTHON
        self.optimizations = [[] for i in range(rop._LAST)]
        for opt in opts:
            for opnum, name in opname.iteritems():
                meth = getattr(opt, 'optimize_' + name.lower(), None)
                if meth is not None:
                    self.optimizations[opnum].append(meth)

    def getnode(self, box):
        try:
            return self.nodes[box]
        except KeyError:
            if isinstance(box, Const):
                node = InstanceNode(box, const=True)
            else:
                node = InstanceNode(box)
            self.nodes[box] = node
            return node

    def getsource(self, box):
        if isinstance(box, Const):
            return box
        return self.nodes[box].source

    def find_nodes(self):
        for op in self.loop.operations:
            if op.is_always_pure():
                is_pure = True
                for arg in op.args:
                    if not self.getnode(arg).const:
                        is_pure = False
                if is_pure:
                    box = op.result
                    assert box is not None
                    self.nodes[box] = self.getnode(box.constbox())
                    continue
            else:
                if op.is_guard():
                    for arg in op.suboperations[0].args:
                        self.getnode(arg)
                # default case
                for box in op.args:
                    self.getnode(box)
            box = op.result
            if box is not None:
                self.nodes[box] = self.getnode(box)

    def new_arguments(self, op):
        newboxes = []
        for box in op.args:
            if isinstance(box, Box):
                instnode = self.nodes[box]
                box = instnode.source
            newboxes.append(box)
        return newboxes

    def optimize_guard(self, op):
        for arg in op.args:
            if not self.getnode(arg).const:
                break
        else:
            return None
        assert len(op.suboperations) == 1
        op_fail = op.suboperations[0]
        op_fail.args = self.new_arguments(op_fail)
        # modification in place. Reason for this is explained in mirror
        # in optimize.py
        op.suboperations = []
        for node, d in self.additional_stores.iteritems():
            for field, fieldnode in d.iteritems():
                op.suboperations.append(ResOperation(rop.SETFIELD_GC,
                    [node.source, fieldnode.source], None, field))
        for node, d in self.additional_setarrayitems.iteritems():
            for field, (fieldnode, descr) in d.iteritems():
                box = fieldnode.source
                op.suboperations.append(ResOperation(rop.SETARRAYITEM_GC,
                                 [node.source, field, box], None, descr))
        op.suboperations.append(op_fail)
        op.args = self.new_arguments(op)
        return op

    def optimize_operations(self):
        self.additional_stores = {}
        self.additional_setarrayitems = {}
        newoperations = []
        for op in self.loop.operations:
            newop = op
            for opt in self.optimizations[op.opnum]:
                newop = opt(op, self)
                if newop is None:
                    break
            if newop is None:
                continue
            if op.is_guard():
                op = self.optimize_guard(op)
                if op is not None:
                    newoperations.append(op)
                continue
            # default handler
            op = op.clone()
            op.args = self.new_arguments(op)
            if op.is_always_pure():
                for box in op.args:
                    if isinstance(box, Box):
                        break
                else:
                    # all constant arguments: constant-fold away
                    box = op.result
                    assert box is not None
                    instnode = InstanceNode(box.constbox(), const=True)
                    self.nodes[box] = instnode
                    continue
            newoperations.append(op)
        print "Length of the loop:", len(newoperations)
        self.loop.operations = newoperations
    
    def optimize_loop(self, loop):
        self.nodes = {}
        self.field_caches = {}
        self.loop = loop
        self.find_nodes()
        self.optimize_operations()

class ConsecutiveGuardClassRemoval(object):
    @staticmethod
    def optimize_guard_class(op, spec):
        instnode = spec.getnode(op.args[0])
        if instnode.cls is not None:
            return None
        instnode.cls = op.args[1]
        return op

class SimpleVirtualizableOpt(object):
    @staticmethod
    def optimize_guard_nonvirtualized(op, spec):
        instnode = spec.getnode(op.args[0])
        instnode.virtualized = True
        instnode.vdesc = op.vdesc
        return None

    @staticmethod
    def optimize_getfield_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return op
        field = op.descr
        if field not in instnode.vdesc.virtuals:
            return op
        node = instnode.cleanfields.get(field, None)
        if node is not None:
            spec.nodes[op.result] = node
            return None
        node = spec.getnode(op.result)
        node.possibly_virtualized_list = True
        instnode.cleanfields[field] = node
        return op

    @staticmethod
    def optimize_setfield_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.virtualized:
            return op
        field = op.descr
        if field not in instnode.vdesc.virtuals:
            return op
        node = spec.getnode(op.args[1])
        instnode.cleanfields[field] = node
        # we never set it here
        d = spec.additional_stores.setdefault(instnode, {})
        d[field] = node
        return None

    @staticmethod
    def optimize_getarrayitem_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.possibly_virtualized_list:
            return op
        if not spec.getnode(op.args[1]).const:
            raise VirtualizedListAccessedWithVariableArg()
        field = spec.getnode(op.args[1]).source
        node = instnode.cleanfields.get(field, None)
        if node is not None:
            spec.nodes[op.result] = node
            return None
        node = spec.getnode(op.result)
        instnode.cleanfields[field] = node
        return op

    @staticmethod
    def optimize_setarrayitem_gc(op, spec):
        instnode = spec.getnode(op.args[0])
        if not instnode.possibly_virtualized_list:
            return op
        argnode = spec.getnode(op.args[1])
        if not argnode.const:
            raise VirtualizedListAccessedWithVariableArg()
        fieldnode = spec.getnode(op.args[2])
        field = argnode.source
        instnode.cleanfields[field] = fieldnode
        d = spec.additional_setarrayitems.setdefault(instnode, {})
        d[field] = (fieldnode, op.descr)
        return None

specializer = Specializer([SimpleVirtualizableOpt(),
                           ConsecutiveGuardClassRemoval()])

def optimize_loop(options, old_loops, loop, cpu=None, spec=specializer):
    if old_loops:
        assert len(old_loops) == 1
        return old_loops[0]
    else:
        spec.optimize_loop(loop)
        return None

def optimize_bridge(options, old_loops, loop, cpu=None, spec=specializer):
    optimize_loop(options, [], loop, cpu, spec)
    return old_loops[0]

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)



