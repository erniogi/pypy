
from _ctypes.basics import _CData, _CDataMeta, ArgumentError, keepalive_key
import _rawffi
import sys
import traceback

# XXX this file needs huge refactoring I fear

class CFuncPtrType(_CDataMeta):
    # XXX write down here defaults and such things

    def _sizeofinstances(self):
        return _rawffi.sizeof('P')

    def _alignmentofinstances(self):
        return _rawffi.alignment('P')

    def _is_pointer_like(self):
        return True

class CFuncPtr(_CData):
    __metaclass__ = CFuncPtrType

    _argtypes_ = None
    _restype_ = None
    _flags_ = 0
    _ffiargshape = 'P'
    _ffishape = 'P'
    _fficompositesize = None
    _needs_free = False
    callable = None
    _ptr = None
    _buffer = None

    def _getargtypes(self):
        return self._argtypes_
    def _setargtypes(self, argtypes):
        self._ptr = None
        self._argtypes_ = argtypes    
    argtypes = property(_getargtypes, _setargtypes)

    def _getrestype(self):
        return self._restype_
    def _setrestype(self, restype):
        self._ptr = None
        from ctypes import c_char_p
        if restype is int:
            from ctypes import c_int
            restype = c_int
        if not isinstance(restype, _CDataMeta) and not restype is None and \
               not callable(restype):
            raise TypeError("Expected ctypes type, got %s" % (restype,))
        self._restype_ = restype
    restype = property(_getrestype, _setrestype)

    def _ffishapes(self, args, restype):
        argtypes = [arg._ffiargshape for arg in args]
        if restype is not None:
            restype = restype._ffiargshape
        else:
            restype = 'O' # void
        return argtypes, restype

    def __init__(self, *args):
        self.name = None
        self._objects = {keepalive_key(0):self}
        self._needs_free = True
        argument = None
        if len(args) == 1:
            argument = args[0]

        if isinstance(argument, (int, long)):
            ffiargs, ffires = self._ffishapes(self._argtypes_, self._restype_)
            self._ptr = _rawffi.FuncPtr(argument, ffiargs, ffires,
                                        self._flags_)
            self._buffer = self._ptr.byptr()
        elif callable(argument):
            self.callable = argument
            ffiargs, ffires = self._ffishapes(self._argtypes_, self._restype_)
            self._ptr = _rawffi.CallbackPtr(self._wrap_callable(argument,
                                                                self.argtypes),
                                            ffiargs, ffires)
            self._buffer = self._ptr.byptr()
        elif isinstance(argument, tuple) and len(argument) == 2:
            import ctypes
            self.name, self.dll = argument
            if isinstance(self.dll, str):
                self.dll = ctypes.CDLL(self.dll)
            # we need to check dll anyway
            ptr = self._getfuncptr([], ctypes.c_int)
            self._buffer = ptr.byptr()

        elif len(args) == 0:
            # this is needed for casts
            self._buffer = _rawffi.Array('P')(1)
            return
        else:
            raise TypeError("Unknown constructor %s" % (argument,))

    def _wrap_callable(self, to_call, argtypes):
        def f(*args):
            if argtypes:
                args = [argtype._CData_retval(argtype.from_address(arg)._buffer)
                        for argtype, arg in zip(argtypes, args)]
            return to_call(*args)
        return f
    
    def __call__(self, *args):
        if self.callable is not None:
            try:
                res = self.callable(*args)
            except:
                exc_info = sys.exc_info()
                traceback.print_tb(exc_info[2], file=sys.stderr)
                print >>sys.stderr, "%s: %s" % (exc_info[0].__name__, exc_info[1])
                return 0
            if self._restype_ is not None:
                return res
            return
        argtypes = self._argtypes_
        if argtypes is None:
            argtypes = self._guess_argtypes(args)
        else:
            dif = len(args) - len(argtypes)
            if dif < 0:
                raise TypeError("Not enough arguments")
            if dif > 0:
                cut = len(args) - dif
                argtypes = argtypes[:] + self._guess_argtypes(args[cut:])
        restype = self._restype_
        funcptr = self._getfuncptr(argtypes, restype)
        argsandobjs = self._wrap_args(argtypes, args)
        resbuffer = funcptr(*[arg._buffer for _, arg in argsandobjs])
        if restype is not None:
            if not isinstance(restype, _CDataMeta):
                return restype(resbuffer[0])
            return restype._CData_retval(resbuffer)

    def _getfuncptr(self, argtypes, restype):
        if self._ptr is not None:
            return self._ptr
        if restype is None or not isinstance(restype, _CDataMeta):
            import ctypes
            restype = ctypes.c_int
        argshapes = [arg._ffiargshape for arg in argtypes]
        resshape = restype._ffiargshape
        if self._buffer is not None:
            self._ptr = _rawffi.FuncPtr(self._buffer[0], argshapes, resshape,
                                        self._flags_)
            return self._ptr

        cdll = self.dll._handle
        try:
            return cdll.ptr(self.name, argshapes, resshape, self._flags_)
        except AttributeError:
            if self._flags_ & _rawffi.FUNCFLAG_CDECL:
                raise

            # For stdcall, try mangled names:
            # funcname -> _funcname@<n>
            # where n is 0, 4, 8, 12, ..., 128
            for i in range(32):
                mangled_name = "_%s@%d" % (self.name, i*4)
                try:
                    return cdll.ptr(mangled_name, argshapes, resshape,
                                    self._flags_)
                except AttributeError:
                    pass
            raise

    @staticmethod
    def _guess_argtypes(args):
        from _ctypes import _CData
        from ctypes import c_char_p, c_wchar_p, c_void_p, c_int
        from ctypes import Array, Structure
        res = []
        for arg in args:
            if hasattr(arg, '_as_parameter_'):
                arg = arg._as_parameter_
            if isinstance(arg, str):
                res.append(c_char_p)
            elif isinstance(arg, unicode):
                res.append(c_wchar_p)
            elif isinstance(arg, _CData):
                res.append(type(arg))
            elif arg is None:
                res.append(c_void_p)
            #elif arg == 0:
            #    res.append(c_void_p)
            elif isinstance(arg, (int, long)):
                res.append(c_int)
            else:
                raise TypeError("Don't know how to handle %s" % (arg,))
        return res

    def _wrap_args(self, argtypes, args):
        try:
            return [argtype._CData_input(arg) for argtype, arg in
                    zip(argtypes, args)]
        except (UnicodeError, TypeError), e:
            raise ArgumentError(str(e))

    def __del__(self):
        if self._needs_free:
            # XXX we need to find a bad guy here
            if self._buffer is None:
                return
            self._buffer.free()
            self._buffer = None
            if isinstance(self._ptr, _rawffi.CallbackPtr):
                self._ptr.free()
                self._ptr = None
            self._needs_free = False
