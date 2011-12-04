from pypy.interpreter.mixedmodule import MixedModule
from pypy.rlib import rmmap

class Module(MixedModule):
    applevel_name = '__builtin_mmap'

    interpleveldefs = {
        'PAGESIZE': 'space.wrap(interp_mmap.PAGESIZE)',
        'ALLOCATIONGRANULARITY': 'space.wrap(interp_mmap.ALLOCATIONGRANULARITY)',
        'ACCESS_READ' : 'space.wrap(interp_mmap.ACCESS_READ)',
        'ACCESS_WRITE': 'space.wrap(interp_mmap.ACCESS_WRITE)',
        'ACCESS_COPY' : 'space.wrap(interp_mmap.ACCESS_COPY)',
        'mmap': 'interp_mmap.W_MMap',
        'error': 'space.fromcache(interp_mmap.Cache).w_error',
    }

    appleveldefs = {
    }
    
    def buildloaders(cls):
        from pypy.module.mmap import interp_mmap
        for constant, value in rmmap.constants.iteritems():
            if isinstance(value, int):
                Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

