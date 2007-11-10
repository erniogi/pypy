from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.ropeobject import W_RopeObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std import slicetype
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.rlib.rarithmetic import intmask, ovfcheck
from pypy.module.unicodedata import unicodedb_3_2_0 as unicodedb
from pypy.tool.sourcetools import func_with_new_name

from pypy.objspace.std.formatting import mod_format

class W_UnicodeObject(W_Object):
    from pypy.objspace.std.unicodetype import unicode_typedef as typedef

    def __init__(w_self, unistr):
        assert isinstance(unistr, unicode)
        w_self._value = unistr

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

    def unwrap(w_self, space):
        # for testing
        return w_self._value
W_UnicodeObject.EMPTY = W_UnicodeObject(u'')

registerimplementation(W_UnicodeObject)

# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected unicode"))
    unistr = w_unistr._value
    result = ['\0'] * len(unistr)
    digits = [ '0', '1', '2', '3', '4',
               '5', '6', '7', '8', '9']
    for i in xrange(len(unistr)):
        uchr = ord(unistr[i])
        if unicodedb.isspace(uchr):
            result[i] = ' '
            continue
        try:
            result[i] = digits[unicodedb.decimal(uchr)]
        except KeyError:
            if 0 < uchr < 256:
                result[i] = chr(uchr)
            else:
                w_encoding = space.wrap('decimal')
                w_start = space.wrap(i)
                w_end = space.wrap(i+1)
                w_reason = space.wrap('invalid decimal Unicode string')
                raise OperationError(space.w_UnicodeEncodeError,space.newtuple ([w_encoding, w_unistr, w_start, w_end, w_reason]))
    return ''.join(result)

# string-to-unicode delegation
def delegate_String2Unicode(space, w_str):
    w_uni =  space.call_function(space.w_unicode, w_str)
    assert isinstance(w_uni, W_UnicodeObject) # help the annotator!
    return w_uni

def str_w__Unicode(space, w_uni):
    return space.str_w(space.str(w_uni))

def unicode_w__Unicode(space, w_uni):
    return w_uni._value

def str__Unicode(space, w_uni):
    return space.call_method(w_uni, 'encode')

def eq__Unicode_Unicode(space, w_left, w_right):
    return space.newbool(w_left._value == w_right._value)

def lt__Unicode_Unicode(space, w_left, w_right):
    left = w_left._value
    right = w_right._value
    return space.newbool(left < right)

def ord__Unicode(space, w_uni):
    if len(w_uni._value) != 1:
        raise OperationError(space.w_TypeError, space.wrap('ord() expected a character'))
    return space.wrap(ord(w_uni._value[0]))

def getnewargs__Unicode(space, w_uni):
    return space.newtuple([W_UnicodeObject(w_uni._value)])

def add__Unicode_Unicode(space, w_left, w_right):
    return W_UnicodeObject(w_left._value + w_right._value)

def add__String_Unicode(space, w_left, w_right):
    return space.add(space.call_function(space.w_unicode, w_left) , w_right)

add__Rope_Unicode = add__String_Unicode

def add__Unicode_String(space, w_left, w_right):
    return space.add(w_left, space.call_function(space.w_unicode, w_right))

add__Unicode_Rope = add__Unicode_String

def contains__String_Unicode(space, w_container, w_item):
    return space.contains(space.call_function(space.w_unicode, w_container), w_item )
contains__Rope_Unicode = contains__String_Unicode


def contains__Unicode_Unicode(space, w_container, w_item):
    item = w_item._value
    container = w_container._value
    return space.newbool(container.find(item) != -1)

def unicode_join__Unicode_ANY(space, w_self, w_list):
    l = space.unpackiterable(w_list)
    delim = w_self._value
    totlen = 0
    if len(l) == 0:
        return W_UnicodeObject.EMPTY
    if (len(l) == 1 and
        space.is_w(space.type(l[0]), space.w_unicode)):
        return l[0]
    
    values_list = []
    for i in range(len(l)):
        item = l[i]
        if space.is_true(space.isinstance(item, space.w_unicode)):
            item = item._value
        elif space.is_true(space.isinstance(item, space.w_str)):
            item = space.unicode_w(item)
        else:
            w_msg = space.mod(space.wrap('sequence item %d: expected string or Unicode'),
                              space.wrap(i))
            raise OperationError(space.w_TypeError, w_msg)
        values_list.append(item)
    return W_UnicodeObject(w_self._value.join(values_list))

def hash__Unicode(space, w_uni):
    s = w_uni._value
    if space.config.objspace.std.withrope:
        # be compatible with the special ropes hash
        # XXX no caching
        if len(s) == 0:
            return space.wrap(0)
        x = 0
        for c in s:
            x = intmask((1000003 * x) + ord(c))
        x <<= 1
        x ^= len(s)
        x ^= ord(s[0])
        h = intmask(x)
        return space.wrap(h)
    if we_are_translated():
        x = hash(s)            # to use the hash cache in rpython strings
    else:
        from pypy.rlib.rarithmetic import _hash_string
        x = _hash_string(s)    # to make sure we get the same hash as rpython
        # (otherwise translation will freeze W_DictObjects where we can't find
        #  the keys any more!)
    return space.wrap(x)

def len__Unicode(space, w_uni):
    return space.wrap(len(w_uni._value))

def getitem__Unicode_ANY(space, w_uni, w_index):
    ival = space.getindex_w(w_index, space.w_IndexError, "string index")
    uni = w_uni._value
    ulen = len(uni)
    if ival < 0:
        ival += ulen
    if ival < 0 or ival >= ulen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("unicode index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return W_UnicodeObject(uni[ival])

def getitem__Unicode_Slice(space, w_uni, w_slice):
    uni = w_uni._value
    length = len(uni)
    start, stop, step, sl = w_slice.indices4(space, length)
    if sl == 0:
        r = []
    elif step == 1:
        assert start >= 0 and stop >= 0
        r = uni[start:stop]
    else:
        r = u"".join([uni[start + i*step] for i in range(sl)])
    return W_UnicodeObject(r)

def mul__Unicode_ANY(space, w_uni, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    uni = w_uni._value
    length = len(uni)
    if times <= 0 or length == 0:
        return W_UnicodeObject.EMPTY
    try:
        result_size = ovfcheck(length * times)
        result = uni * times
    except (OverflowError, MemoryError):
        raise OperationError(space.w_OverflowError, space.wrap('repeated string is too long'))
    return W_UnicodeObject(result)

def mul__ANY_Unicode(space, w_times, w_uni):
    return mul__Unicode_ANY(space, w_uni, w_times)

def _isspace(uchar):
    return unicodedb.isspace(ord(uchar))

def make_generic(funcname):
    def func(space, w_self): 
        v = w_self._value
        if len(v) == 0:
            return space.w_False
        for idx in range(len(v)):
            if not getattr(unicodedb, funcname)(ord(v[idx])):
                return space.w_False
        return space.w_True
    return func_with_new_name(func, "unicode_%s__Unicode" % (funcname, ))

unicode_isspace__Unicode = make_generic("isspace")
unicode_isalpha__Unicode = make_generic("isalpha")
unicode_isalnum__Unicode = make_generic("isalnum")
unicode_isdecimal__Unicode = make_generic("isdecimal")
unicode_isdigit__Unicode = make_generic("isdigit")
unicode_isnumeric__Unicode = make_generic("isnumeric")

def unicode_islower__Unicode(space, w_unicode):
    cased = False
    for uchar in w_unicode._value:
        if (unicodedb.isupper(ord(uchar)) or
            unicodedb.istitle(ord(uchar))):
            return space.w_False
        if not cased and unicodedb.islower(ord(uchar)):
            cased = True
    return space.newbool(cased)

def unicode_isupper__Unicode(space, w_unicode):
    cased = False
    for uchar in w_unicode._value:
        if (unicodedb.islower(ord(uchar)) or
            unicodedb.istitle(ord(uchar))):
            return space.w_False
        if not cased and unicodedb.isupper(ord(uchar)):
            cased = True
    return space.newbool(cased)

def unicode_istitle__Unicode(space, w_unicode):
    cased = False
    previous_is_cased = False
    for uchar in w_unicode._value:
        if (unicodedb.isupper(ord(uchar)) or
            unicodedb.istitle(ord(uchar))):
            if previous_is_cased:
                return space.w_False
            previous_is_cased = cased = True
        elif unicodedb.islower(ord(uchar)):
            if not previous_is_cased:
                return space.w_False
            previous_is_cased = cased = True
        else:
            previous_is_cased = False
    return space.newbool(cased)

def _strip(space, w_self, w_chars, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    u_chars = w_chars._value
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        while lpos < rpos and u_self[lpos] in u_chars:
           lpos += 1
       
    if right:
        while rpos > lpos and u_self[rpos - 1] in u_chars:
           rpos -= 1
           
    assert rpos >= 0
    result = u_self[lpos: rpos]
    return W_UnicodeObject(result)

def _strip_none(space, w_self, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        while lpos < rpos and _isspace(u_self[lpos]):
           lpos += 1
       
    if right:
        while rpos > lpos and _isspace(u_self[rpos - 1]):
           rpos -= 1
       
    assert rpos >= 0
    result = u_self[lpos: rpos]
    return W_UnicodeObject(result)

def unicode_strip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 1)
def unicode_strip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 1)
def unicode_strip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'strip',
                             space.call_function(space.w_unicode, w_chars))
unicode_strip__Unicode_Rope = unicode_strip__Unicode_String

def unicode_lstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 0)
def unicode_lstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 0)
def unicode_lstrip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'lstrip',
                             space.call_function(space.w_unicode, w_chars))

unicode_lstrip__Unicode_Rope = unicode_lstrip__Unicode_String

def unicode_rstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 0, 1)
def unicode_rstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 0, 1)
def unicode_rstrip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'rstrip',
                             space.call_function(space.w_unicode, w_chars))

unicode_rstrip__Unicode_Rope = unicode_rstrip__Unicode_String

def unicode_capitalize__Unicode(space, w_self):
    input = w_self._value
    if len(input) == 0:
        return W_UnicodeObject.EMPTY
    result = [u'\0'] * len(input)
    result[0] = unichr(unicodedb.toupper(ord(input[0])))
    for i in range(1, len(input)):
        result[i] = unichr(unicodedb.tolower(ord(input[i])))
    return W_UnicodeObject(u''.join(result))

def unicode_title__Unicode(space, w_self):
    input = w_self._value
    if len(input) == 0:
        return w_self
    result = [u'\0'] * len(input)

    previous_is_cased = False
    for i in range(len(input)):
        unichar = ord(input[i])
        if previous_is_cased:
            result[i] = unichr(unicodedb.tolower(unichar))
        else:
            result[i] = unichr(unicodedb.totitle(unichar))
        previous_is_cased = unicodedb.iscased(unichar)
    return W_UnicodeObject(u''.join(result))

def unicode_lower__Unicode(space, w_self):
    input = w_self._value
    result = [u'\0'] * len(input)
    for i in range(len(input)):
        result[i] = unichr(unicodedb.tolower(ord(input[i])))
    return W_UnicodeObject(u''.join(result))

def unicode_upper__Unicode(space, w_self):
    input = w_self._value
    result = [u'\0'] * len(input)
    for i in range(len(input)):
        result[i] = unichr(unicodedb.toupper(ord(input[i])))
    return W_UnicodeObject(u''.join(result))

def unicode_swapcase__Unicode(space, w_self):
    input = w_self._value
    result = [u'\0'] * len(input)
    for i in range(len(input)):
        unichar = ord(input[i])
        if unicodedb.islower(unichar):
            result[i] = unichr(unicodedb.toupper(unichar))
        elif unicodedb.isupper(unichar):
            result[i] = unichr(unicodedb.tolower(unichar))
        else:
            result[i] = input[i]
    return W_UnicodeObject(u''.join(result))

def _normalize_index(length, index):
    if index < 0:
        index += length
        if index < 0:
            index = 0
    elif index > length:
        index = length
    return index

def _convert_idx_params(space, w_self, w_start, w_end):
    self = w_self._value
    start = slicetype.adapt_bound(space, len(self), w_start)
    end = slicetype.adapt_bound(space, len(self), w_end)

    assert start >= 0
    assert end >= 0

    return (self, start, end)

def unicode_endswith__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    substr = w_substr._value
    substr_len = len(substr)
    
    if end - start < substr_len:
        return space.w_False # substring is too long
    start = end - substr_len
    for i in range(substr_len):
        if self[start + i] != substr[i]:
            return space.w_False
    return space.w_True

def unicode_startswith__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)

    substr = w_substr._value
    substr_len = len(substr)
    
    if end - start < substr_len:
        return space.w_False # substring is too long
    
    for i in range(substr_len):
        if self[start + i] != substr[i]:
            return space.w_False
    return space.w_True


def unicode_startswith__Unicode_Tuple_ANY_ANY(space, w_unistr, w_prefixes,
                                              w_start, w_end):
    unistr, start, end = _convert_idx_params(space, w_unistr, w_start, w_end)
    for w_prefix in space.unpacktuple(w_prefixes):
        prefix = space.unicode_w(w_prefix)
        if unistr.startswith(prefix, start, end):
            return space.w_True
    return space.w_False

def unicode_endswith__Unicode_Tuple_ANY_ANY(space, w_unistr, w_suffixes,
                                            w_start, w_end):
    unistr, start, end = _convert_idx_params(space, w_unistr, w_start, w_end)
    for w_suffix in space.unpacktuple(w_suffixes):
        suffix = space.unicode_w(w_suffix)
        if unistr.endswith(suffix, start, end):
            return space.w_True
    return space.w_False

def _to_unichar_w(space, w_char):
    try:
        unistr = space.unicode_w(w_char)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            msg = 'The fill character cannot be converted to Unicode'
            raise OperationError(space.w_TypeError, space.wrap(msg))
        else:
            raise

    if len(unistr) != 1:
        raise OperationError(space.w_TypeError, space.wrap('The fill character must be exactly one character long'))
    return unistr[0]

def unicode_center__Unicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._value
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - len(self)
    if padding < 0:
        return space.call_function(space.w_unicode, w_self)
    leftpad = padding // 2 + (padding & width & 1)
    result = [fillchar] * width
    for i in range(len(self)):
        result[leftpad + i] = self[i]
    return W_UnicodeObject(u''.join(result))

def unicode_ljust__Unicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._value
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - len(self)
    if padding < 0:
        return space.call_function(space.w_unicode, w_self)
    result = [fillchar] * width
    for i in range(len(self)):
        result[i] = self[i]
    return W_UnicodeObject(u''.join(result))

def unicode_rjust__Unicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._value
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - len(self)
    if padding < 0:
        return space.call_function(space.w_unicode, w_self)
    result = [fillchar] * width
    for i in range(len(self)):
        result[padding + i] = self[i]
    return W_UnicodeObject(u''.join(result))
    
def unicode_zfill__Unicode_ANY(space, w_self, w_width):
    self = w_self._value
    width = space.int_w(w_width)
    if len(self) == 0:
        return W_UnicodeObject(u'0' * width)
    padding = width - len(self)
    if padding <= 0:
        return space.call_function(space.w_unicode, w_self)
    result = [u'0'] * width
    for i in range(len(self)):
        result[padding + i] = self[i]
    # Move sign to first position
    if self[0] in (u'+', u'-'):
        result[0] = self[0]
        result[padding] = u'0'
    return W_UnicodeObject(u''.join(result))

def unicode_splitlines__Unicode_ANY(space, w_self, w_keepends):
    self = w_self._value
    keepends = 0
    if space.int_w(w_keepends):
        keepends = 1
    if len(self) == 0:
        return space.newlist([])
    
    start = 0
    end = len(self)
    pos = 0
    lines = []
    while pos < end:
        if unicodedb.islinebreak(ord(self[pos])):
            if (self[pos] == u'\r' and pos + 1 < end and
                self[pos + 1] == u'\n'):
                # Count CRLF as one linebreak
                lines.append(W_UnicodeObject(self[start:pos + keepends * 2]))
                pos += 1
            else:
                lines.append(W_UnicodeObject(self[start:pos + keepends]))
            pos += 1
            start = pos
        else:
            pos += 1
    if not unicodedb.islinebreak(ord(self[end - 1])):
        lines.append(W_UnicodeObject(self[start:]))
    return space.newlist(lines)

def unicode_find__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    substr = w_substr._value
    return space.wrap(self.find(substr, start, end))

def unicode_rfind__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    substr = w_substr._value
    return space.wrap(self.rfind(substr, start, end))

def unicode_index__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    substr = w_substr._value
    index = self.find(substr, start, end)
    if index < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('substring not found'))
    return space.wrap(index)

def unicode_rindex__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    substr = w_substr._value
    index = self.rfind(substr, start, end)
    if index < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('substring not found'))
    return space.wrap(index)

def unicode_count__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    substr = w_substr._value
    return space.wrap(self.count(substr, start, end))

def unicode_split__Unicode_None_ANY(space, w_self, w_none, w_maxsplit):
    self = w_self._value
    maxsplit = space.int_w(w_maxsplit)
    parts = []
    if len(self) == 0:
        return space.newlist([])
    start = 0
    end = len(self)
    inword = 0

    while maxsplit != 0 and start < end:
        index = start
        for index in range(start, end):
            if _isspace(self[index]):
                break
            else:
                inword = 1
        else:
            break
        if inword == 1:
            parts.append(W_UnicodeObject(self[start:index]))
            maxsplit -= 1
        # Eat whitespace
        for start in range(index + 1, end):
            if not _isspace(self[start]):
                break
        else:
            return space.newlist(parts)

    parts.append(W_UnicodeObject(self[start:]))
    return space.newlist(parts)

def unicode_split__Unicode_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
    self = w_self._value
    delim = w_delim._value
    maxsplit = space.int_w(w_maxsplit)
    delim_len = len(delim)
    if delim_len == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('empty separator'))
    parts = _split_with(self, delim, maxsplit)
    return space.newlist([W_UnicodeObject(part) for part in parts])


def unicode_rsplit__Unicode_None_ANY(space, w_self, w_none, w_maxsplit):
    self = w_self._value
    maxsplit = space.int_w(w_maxsplit)
    parts = []
    if len(self) == 0:
        return space.newlist([])
    start = 0
    end = len(self)
    inword = 0

    while maxsplit != 0 and start < end:
        index = end
        for index in range(end-1, start-1, -1):
            if _isspace(self[index]):
                break
            else:
                inword = 1
        else:
            break
        if inword == 1:
            parts.append(W_UnicodeObject(self[index+1:end]))
            maxsplit -= 1
        # Eat whitespace
        for end in range(index, start-1, -1):
            if not _isspace(self[end-1]):
                break
        else:
            return space.newlist(parts)

    parts.append(W_UnicodeObject(self[:end]))
    parts.reverse()
    return space.newlist(parts)

def unicode_rsplit__Unicode_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
    self = w_self._value
    delim = w_delim._value
    maxsplit = space.int_w(w_maxsplit)
    delim_len = len(delim)
    if delim_len == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('empty separator'))
    parts = []
    if len(self) == 0:
        return space.newlist([])
    start = 0
    end = len(self)
    while maxsplit != 0:
        index = self.rfind(delim, 0, end)
        if index < 0:
            break
        parts.append(W_UnicodeObject(self[index+delim_len:end]))
        end = index
        maxsplit -= 1
    parts.append(W_UnicodeObject(self[:end]))
    parts.reverse()
    return space.newlist(parts)

def _split_into_chars(self, maxsplit):
    if maxsplit == 0:
        return [self]
    index = 0
    end = len(self)
    parts = [u'']
    maxsplit -= 1
    while maxsplit != 0:
        if index >= end:
            break
        parts.append(self[index])
        index += 1
        maxsplit -= 1
    parts.append(self[index:])
    return parts

def _split_with(self, with_, maxsplit):
    parts = []
    start = 0
    end = len(self)
    length = len(with_)
    while maxsplit != 0:
        index = self.find(with_, start, end)
        if index < 0:
            break
        parts.append(self[start:index])
        start = index + length
        maxsplit -= 1
    parts.append(self[start:])
    return parts

def unicode_replace__Unicode_Unicode_Unicode_ANY(space, w_self, w_old,
                                                 w_new, w_maxsplit):
    if len(w_old._value):
        parts = _split_with(w_self._value, w_old._value,
                            space.int_w(w_maxsplit))
    else:
        self = w_self._value
        maxsplit = space.int_w(w_maxsplit)
        parts = _split_into_chars(self, maxsplit)
    return W_UnicodeObject(w_new._value.join(parts))
    

app = gateway.applevel(r'''
import sys

def unicode_expandtabs__Unicode_ANY(self, tabsize):
    parts = self.split(u'\t')
    result = [ parts[0] ]
    prevsize = 0
    for ch in parts[0]:
        prevsize += 1
        if ch in (u"\n", u"\r"):
            prevsize = 0
    for i in range(1, len(parts)):
        pad = tabsize - prevsize % tabsize
        result.append(u' ' * pad)
        nextpart = parts[i]
        result.append(nextpart)
        prevsize = 0
        for ch in nextpart:
            prevsize += 1
            if ch in (u"\n", u"\r"):
                prevsize = 0
    return u''.join(result)

def unicode_translate__Unicode_ANY(self, table):
    result = []
    for unichar in self:
        try:
            newval = table[ord(unichar)]
        except KeyError:
            result.append(unichar)
        else:
            if newval is None:
                continue
            elif isinstance(newval, int):
                if newval < 0 or newval > sys.maxunicode:
                    raise TypeError("character mapping must be in range(0x%x)"%(sys.maxunicode + 1,))
                result.append(unichr(newval))
            elif isinstance(newval, unicode):
                result.append(newval)
            else:
                raise TypeError("character mapping must return integer, None or unicode")
    return ''.join(result)

def unicode_encode__Unicode_ANY_ANY(unistr, encoding=None, errors=None):
    import codecs, sys
    if encoding is None:
        encoding = sys.getdefaultencoding()

    encoder = codecs.getencoder(encoding)
    if errors is None:
        retval, lenght = encoder(unistr)
    else:
        retval, length = encoder(unistr, errors)
    if not isinstance(retval,str):
        raise TypeError("encoder did not return a string object (type=%s)" %
                        type(retval).__name__)
    return retval



''')



unicode_expandtabs__Unicode_ANY = app.interphook('unicode_expandtabs__Unicode_ANY')
unicode_translate__Unicode_ANY = app.interphook('unicode_translate__Unicode_ANY')
unicode_encode__Unicode_ANY_ANY = app.interphook('unicode_encode__Unicode_ANY_ANY')

def unicode_partition__Unicode_Unicode(space, w_unistr, w_unisub):
    unistr = w_unistr._value
    unisub = w_unisub._value
    if not unisub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = unistr.find(unisub)
    if pos == -1:
        return space.newtuple([w_unistr, W_UnicodeObject.EMPTY,
                               W_UnicodeObject.EMPTY])
    else:
        return space.newtuple([space.wrap(unistr[:pos]), w_unisub,
                               space.wrap(unistr[pos+len(unisub):])])

def unicode_rpartition__Unicode_Unicode(space, w_unistr, w_unisub):
    unistr = w_unistr._value
    unisub = w_unisub._value
    if not unisub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = unistr.rfind(unisub)
    if pos == -1:
        return space.newtuple([W_UnicodeObject.EMPTY,
                               W_UnicodeObject.EMPTY, w_unistr])
    else:
        return space.newtuple([space.wrap(unistr[:pos]), w_unisub,
                               space.wrap(unistr[pos+len(unisub):])])


# Move this into the _codecs module as 'unicodeescape_string (Remember to cater for quotes)'
def repr__Unicode(space, w_unicode):
    hexdigits = "0123456789abcdef"
    chars = w_unicode._value
    size = len(chars)
    
    singlequote = doublequote = False
    for c in chars:
        if c == u'\'':
            singlequote = True
        elif c == u'"':
            doublequote = True
    if singlequote and not doublequote:
        quote = '"'
    else:
        quote = '\''
    result = ['\0'] * (3 + size*6)
    result[0] = 'u'
    result[1] = quote
    i = 2
    j = 0
    while j<len(chars):
        ch = chars[j]
##        if ch == u"'":
##            quote ='''"'''
##            result[1] = quote
##            result[i] = '\''
##            #result[i + 1] = "'"
##            i += 1
##            continue
        code = ord(ch)
        if code >= 0x10000:
            # Resize if needed
            if i + 12 > len(result):
                result.extend(['\0'] * 100)
            result[i] = '\\'
            result[i + 1] = "U"
            result[i + 2] = hexdigits[(code >> 28) & 0xf] 
            result[i + 3] = hexdigits[(code >> 24) & 0xf] 
            result[i + 4] = hexdigits[(code >> 20) & 0xf] 
            result[i + 5] = hexdigits[(code >> 16) & 0xf] 
            result[i + 6] = hexdigits[(code >> 12) & 0xf] 
            result[i + 7] = hexdigits[(code >>  8) & 0xf] 
            result[i + 8] = hexdigits[(code >>  4) & 0xf] 
            result[i + 9] = hexdigits[(code >>  0) & 0xf]
            i += 10
            j += 1
            continue
        if code >= 0xD800 and code < 0xDC00:
            if j < size - 1:
                ch2 = chars[j+1]
                code2 = ord(ch2)
                if code2 >= 0xDC00 and code2 <= 0xDFFF:
                    code = (((code & 0x03FF) << 10) | (code2 & 0x03FF)) + 0x00010000
                    if i + 12 > len(result):
                        result.extend(['\0'] * 100)
                    result[i] = '\\'
                    result[i + 1] = "U"
                    result[i + 2] = hexdigits[(code >> 28) & 0xf] 
                    result[i + 3] = hexdigits[(code >> 24) & 0xf] 
                    result[i + 4] = hexdigits[(code >> 20) & 0xf] 
                    result[i + 5] = hexdigits[(code >> 16) & 0xf] 
                    result[i + 6] = hexdigits[(code >> 12) & 0xf] 
                    result[i + 7] = hexdigits[(code >>  8) & 0xf] 
                    result[i + 8] = hexdigits[(code >>  4) & 0xf] 
                    result[i + 9] = hexdigits[(code >>  0) & 0xf]
                    i += 10
                    j += 2
                    continue
                
        if code >= 0x100:
            result[i] = '\\'
            result[i + 1] = "u"
            result[i + 2] = hexdigits[(code >> 12) & 0xf] 
            result[i + 3] = hexdigits[(code >>  8) & 0xf] 
            result[i + 4] = hexdigits[(code >>  4) & 0xf] 
            result[i + 5] = hexdigits[(code >>  0) & 0xf] 
            i += 6
            j += 1
            continue
        if code == ord('\\') or code == ord(quote):
            result[i] = '\\'
            result[i + 1] = chr(code)
            i += 2
            j += 1
            continue
        if code == ord('\t'):
            result[i] = '\\'
            result[i + 1] = "t"
            i += 2
            j += 1
            continue
        if code == ord('\r'):
            result[i] = '\\'
            result[i + 1] = "r"
            i += 2
            j += 1
            continue
        if code == ord('\n'):
            result[i] = '\\'
            result[i + 1] = "n"
            i += 2
            j += 1
            continue
        if code < ord(' ') or code >= 0x7f:
            result[i] = '\\'
            result[i + 1] = "x"
            result[i + 2] = hexdigits[(code >> 4) & 0xf] 
            result[i + 3] = hexdigits[(code >> 0) & 0xf] 
            i += 4
            j += 1
            continue
        result[i] = chr(code)
        i += 1
        j += 1
    result[i] = quote
    i += 1
    return space.wrap(''.join(result[:i]))
        

def mod__Unicode_ANY(space, w_format, w_values):
    return mod_format(space, w_format, w_values, do_unicode=True)


import unicodetype
register_all(vars(), unicodetype)

# str.strip(unicode) needs to convert self to unicode and call unicode.strip we
# use the following magic to register strip_string_unicode as a String
# multimethod.

# XXX couldn't string and unicode _share_ the multimethods that make up their
# methods?

class str_methods:
    import stringtype
    W_UnicodeObject = W_UnicodeObject
    from pypy.objspace.std.stringobject import W_StringObject
    from pypy.objspace.std.ropeobject import W_RopeObject
    def str_strip__String_Unicode(space, w_self, w_chars):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'strip', w_chars)
    str_strip__Rope_Unicode = str_strip__String_Unicode
    def str_lstrip__String_Unicode(space, w_self, w_chars):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'lstrip', w_chars)
    str_lstrip__Rope_Unicode = str_lstrip__String_Unicode
    def str_rstrip__String_Unicode(space, w_self, w_chars):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'rstrip', w_chars)
    str_rstrip__Rope_Unicode = str_rstrip__String_Unicode
    def str_count__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'count', w_substr, w_start, w_end)
    str_count__Rope_Unicode_ANY_ANY = str_count__String_Unicode_ANY_ANY
    def str_find__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'find', w_substr, w_start, w_end)
    str_find__Rope_Unicode_ANY_ANY = str_find__String_Unicode_ANY_ANY
    def str_rfind__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'rfind', w_substr, w_start, w_end)
    str_rfind__Rope_Unicode_ANY_ANY = str_rfind__String_Unicode_ANY_ANY
    def str_index__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'index', w_substr, w_start, w_end)
    str_index__Rope_Unicode_ANY_ANY = str_index__String_Unicode_ANY_ANY
    def str_rindex__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'rindex', w_substr, w_start, w_end)
    str_rindex__Rope_Unicode_ANY_ANY = str_rindex__String_Unicode_ANY_ANY
    def str_replace__String_Unicode_Unicode_ANY(space, w_self, w_old, w_new, w_maxsplit):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'replace', w_old, w_new, w_maxsplit)
    str_replace__Rope_Unicode_Unicode_ANY = str_replace__String_Unicode_Unicode_ANY
    def str_split__String_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'split', w_delim, w_maxsplit)
    str_split__Rope_Unicode_ANY = str_split__String_Unicode_ANY
    def str_rsplit__String_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'rsplit', w_delim, w_maxsplit)
    str_rsplit__Rope_Unicode_ANY = str_rsplit__String_Unicode_ANY
    register_all(vars(), stringtype)
