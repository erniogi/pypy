"""
Module objects.
"""

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError

class Module(Wrappable):
    """A module."""

    def __init__(self, space, w_name, w_dict=None):
        self.space = space
        if w_dict is None: 
            w_dict = space.newdict([])
        self.w_dict = w_dict 
        self.descr_module__init__(w_name)

    def getdict(self):
        return self.w_dict

    def setdict(self, w_dict):
        self.w_dict = w_dict

    def descr_module__new__(space, w_subtype, __args__):
        module = space.allocate_instance(Module, w_subtype)
        module.__init__(space, space.wrap('?'))
        return space.wrap(module)

    def descr_module__init__(self, w_name, w_doc=None):
        space = self.space
        self.w_name = w_name
        if w_doc is None:  
            w_doc = space.w_None
        w_dict = self.getdict()
        space.setitem(w_dict, space.wrap('__name__'), w_name)
        space.setitem(w_dict, space.wrap('__doc__'), w_doc)

    def descr_module__getattribute__(self, w_attr):
        space = self.space
        w_self = space.wrap(self)
        attr = space.str_w(w_attr)
        w_result = space.lookup(w_self, attr) 
        if w_result is None:
            return self.get(attr) 
        else:
            return space.get(w_result, w_self)

    def get(self, attr): 
        space = self.space
        try: 
            return space.getitem(self.w_dict, self.space.wrap(attr))
        except OperationError, e: 
            if not e.match(space, space.w_KeyError): 
                raise 
        # ______ for the 'sys' module only _____ XXX put that
        # into a special subclass at some point 
        if self is space.sys:
            if attr == 'exc_type':
                operror = space.getexecutioncontext().sys_exc_info()
                if operror is None:
                    return space.w_None
                else:
                    return operror.w_type
            if attr == 'exc_value':
                operror = space.getexecutioncontext().sys_exc_info()
                if operror is None:
                    return space.w_None
                else:
                    return operror.w_value
            if attr == 'exc_traceback':
                operror = space.getexecutioncontext().sys_exc_info()
                if operror is None:
                    return space.w_None
                else:
                    return space.wrap(operror.application_traceback)
        # produce a nice error message that shows the name of the module
        try:
            name = space.str_w(self.w_name)
        except OperationError:
            name = '?'
        msg = "'%s' module has no attribute '%s'" % (name, attr)
        raise OperationError(space.w_AttributeError, space.wrap(msg))
