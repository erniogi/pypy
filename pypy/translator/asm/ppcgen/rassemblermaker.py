from pypy.tool.sourcetools import compile2

from pypy.translator.asm.ppcgen.form import IDesc

##     "opcode": ( 0,  5),
##     "rA":     (11, 15, 'unsigned', regname._R),
##     "rB":     (16, 20, 'unsigned', regname._R),
##     "Rc":     (31, 31),
##     "rD":     ( 6, 10, 'unsigned', regname._R),
##     "OE":     (21, 21),
##     "XO2":    (22, 30),

## XO = Form("rD", "rA", "rB", "OE", "XO2", "Rc")

##     add   = XO(31, XO2=266, OE=0, Rc=0)

##     def add(rD, rA, rB):
##         v = 0
##         v |= (31&(2**(5-0+1)-1)) << (32-5-1)
##         ...
##         return v

def make_func(name, desc):
    sig = []
    fieldvalues = []
    for field in desc.fields:
        if field in desc.specializations:
            fieldvalues.append((field, desc.specializations[field]))
        else:
            sig.append(field.name)
            fieldvalues.append((field, field.name))
    body = ['v = 0']
    assert 'v' not in sig # that wouldn't be funny
    #body.append('print %r'%name + ', ' + ', '.join(["'%s:', %s"%(s, s) for s in sig]))
    for field, value in fieldvalues:
        body.append('v |= (%3s & %#05x) << %d'%(value,
                                           field.mask,
                                           (32 - field.right - 1)))
    body.append('self.emit(v)')
    src = 'def %s(self, %s):\n    %s'%(name, ', '.join(sig), '\n    '.join(body))
    d = {}
    #print src
    exec compile2(src) in d
    return d[name]

def make_rassembler(cls):
    bases = [make_rassembler(b) for b in cls.__bases__]
    ns = {}
    for k, v in cls.__dict__.iteritems():
        if isinstance(v, IDesc):
            v = make_func(k, v)
        ns[k] = v
    rcls = type('R' + cls.__name__, tuple(bases), ns)
    def emit(self, value):
        self.insts.append(value)
    rcls.emit = emit
    return rcls
