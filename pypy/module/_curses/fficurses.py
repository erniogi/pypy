
""" The ffi for rpython, need to be imported for side effects
"""

import sys
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.extfunc import register_external
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.module._curses import interp_curses
from pypy.rpython.lltypesystem import llmemory

# waaa...
includes = ['curses.h', 'term.h']
libs = ['curses']

INT = rffi.INT
INTP = lltype.Ptr(lltype.Array(INT, hints={'nolength':True}))
c_setupterm = rffi.llexternal('setupterm', [rffi.CCHARP, INT, INTP], INT,
                              includes=includes, libraries=libs)
c_tigetstr = rffi.llexternal('tigetstr', [rffi.CCHARP], rffi.CCHARP,
                             includes=includes, libraries=libs)
c_tparm = rffi.llexternal('tparm', [rffi.CCHARP, INT, INT, INT, INT, INT,
                                    INT, INT, INT, INT, INT], rffi.CCHARP,
                          includes=includes, libraries=libs)

ERR = rffi.CConstant('ERR', INT)
OK = rffi.CConstant('OK', INT)

def curses_setupterm(term, fd):
    intp = lltype.malloc(INTP.TO, 1, flavor='raw')
    err = c_setupterm(term, fd, intp)
    try:
        if err == ERR:
            if intp[0] == 0:
                msg = "setupterm: could not find terminal"
            elif intp[0] == -1:
                msg = "setupterm: could not find terminfo database"
            else:
                msg = "setupterm: unknown error"
            raise interp_curses.curses_error(msg)
        interp_curses.module_info.setupterm_called = True
    finally:
        lltype.free(intp, flavor='raw')

def curses_setupterm_null_llimpl(fd):
    curses_setupterm(lltype.nullptr(rffi.CCHARP.TO), fd)

def curses_setupterm_llimpl(term, fd):
    ll_s = rffi.str2charp(term)
    try:
        curses_setupterm(ll_s, fd)
    finally:
        lltype.free(ll_s, flavor='raw')

register_external(interp_curses._curses_setupterm_null,
                  [int], llimpl=curses_setupterm_null_llimpl,
                  export_name='_curses.setupterm_null')
register_external(interp_curses._curses_setupterm,
                  [str, int], llimpl=curses_setupterm_llimpl,
                  export_name='_curses.setupterm')

def check_setup_invoked():
    if not interp_curses.module_info.setupterm_called:
        raise interp_curses.curses_error("must call (at least) setupterm() first")

def tigetstr_llimpl(cap):
    check_setup_invoked()
    ll_cap = rffi.str2charp(cap)
    try:
        ll_res = c_tigetstr(ll_cap)
        num = lltype.cast_ptr_to_int(ll_res)
        if num == 0 or num == -1:
            raise interp_curses.TermError()
        res = rffi.charp2str(ll_res)
        # XXX - how to avoid a problem with leaking stuff here???
        #lltype.free(ll_res, flavor='raw')
        return res
    finally:
        lltype.free(ll_cap, flavor='raw')
    
register_external(interp_curses._curses_tigetstr, [str], str,
                  export_name='_curses.tigetstr', llimpl=tigetstr_llimpl)

def tparm_llimpl(s, args):
    check_setup_invoked()
    l = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for i in range(min(len(args), 10)):
        l[i] = args[i]
    ll_s = rffi.str2charp(s)
    # XXX nasty trick stolen from CPython
    ll_res = c_tparm(ll_s, l[0], l[1], l[2], l[3], l[4], l[5], l[6],
                     l[7], l[8], l[9])
    lltype.free(ll_s, flavor='raw')
    # XXX - how to make this happy?
    #lltype.free(ll_res, flavor.raw)
    return rffi.charp2str(ll_res)

register_external(interp_curses._curses_tparm, [str, [int]], str,
                  export_name='_curses.tparm', llimpl=tparm_llimpl)

