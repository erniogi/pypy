import sys

if sys.maxint > 2**32:
    MAXREPEAT = int(2**32 - 1)
    MAXGROUPS = int(2**31 - 1)
else:
    MAXREPEAT = int(2**31 - 1)
    MAXGROUPS = int(2**30 - 1)

# In _sre.c this is bytesize of the code word type of the C implementation.
# There it's 2 for normal Python builds and more for wide unicode builds (large
# enough to hold a 32-bit UCS-4 encoded character). Since here in pure Python
# we only see re bytecodes as Python longs, we shouldn't have to care about the
# codesize. But sre_compile will compile some stuff differently depending on the
# codesize (e.g., charsets).
from rpython.rlib.runicode import MAXUNICODE
if MAXUNICODE == 65535:
    CODESIZE = 2
else:
    CODESIZE = 4

_CODEBITS = CODESIZE * 8

OPCODE_FAILURE            = 0
OPCODE_SUCCESS            = 1
OPCODE_ANY                = 2
OPCODE_ANY_ALL            = 3
OPCODE_ASSERT             = 4
OPCODE_ASSERT_NOT         = 5
OPCODE_AT                 = 6
OPCODE_BRANCH             = 7
#OPCODE_CALL              = 8
OPCODE_CATEGORY           = 9
OPCODE_CHARSET            = 10
OPCODE_BIGCHARSET         = 11
OPCODE_GROUPREF           = 12
OPCODE_GROUPREF_EXISTS    = 13
OPCODE_GROUPREF_IGNORE    = 14
OPCODE_IN                 = 15
OPCODE_IN_IGNORE          = 16
OPCODE_INFO               = 17
OPCODE_JUMP               = 18
OPCODE_LITERAL            = 19
OPCODE_LITERAL_IGNORE     = 20
OPCODE_MARK               = 21
OPCODE_MAX_UNTIL          = 22
OPCODE_MIN_UNTIL          = 23
OPCODE_NOT_LITERAL        = 24
OPCODE_NOT_LITERAL_IGNORE = 25
OPCODE_NEGATE             = 26
OPCODE_RANGE              = 27
OPCODE_REPEAT             = 28
OPCODE_REPEAT_ONE         = 29
#OPCODE_SUBPATTERN        = 30
OPCODE_MIN_REPEAT_ONE     = 31
OPCODE_RANGE_IGNORE       = 32

# not used by Python itself
OPCODE_UNICODE_GENERAL_CATEGORY = 70

opnames = {}
for entry, value in globals().items():
    if entry.startswith("OPCODE_"):
        opnames[value] = entry[len("OPCODE_"):]


AT_BEGINNING = 0
AT_BEGINNING_LINE = 1
AT_BEGINNING_STRING = 2
AT_BOUNDARY = 3
AT_NON_BOUNDARY = 4
AT_END = 5
AT_END_LINE = 6
AT_END_STRING = 7
AT_LOC_BOUNDARY = 8
AT_LOC_NON_BOUNDARY = 9
AT_UNI_BOUNDARY = 10
AT_UNI_NON_BOUNDARY = 11

def _makecodes(s):
    d = {}
    g = globals()
    for i, name in enumerate(s.strip().split()):
        d[i] = name
        g[name] = i
    return d

ATCODES = _makecodes("""
    AT_BEGINNING AT_BEGINNING_LINE AT_BEGINNING_STRING
    AT_BOUNDARY AT_NON_BOUNDARY
    AT_END AT_END_LINE AT_END_STRING
    AT_LOC_BOUNDARY AT_LOC_NON_BOUNDARY
    AT_UNI_BOUNDARY AT_UNI_NON_BOUNDARY
""")

# categories
CHCODES = _makecodes("""
    CATEGORY_DIGIT CATEGORY_NOT_DIGIT
    CATEGORY_SPACE CATEGORY_NOT_SPACE
    CATEGORY_WORD CATEGORY_NOT_WORD
    CATEGORY_LINEBREAK CATEGORY_NOT_LINEBREAK
    CATEGORY_LOC_WORD CATEGORY_LOC_NOT_WORD
    CATEGORY_UNI_DIGIT CATEGORY_UNI_NOT_DIGIT
    CATEGORY_UNI_SPACE CATEGORY_UNI_NOT_SPACE
    CATEGORY_UNI_WORD CATEGORY_UNI_NOT_WORD
    CATEGORY_UNI_LINEBREAK CATEGORY_UNI_NOT_LINEBREAK
""")

SRE_INFO_PREFIX = 1
SRE_INFO_LITERAL = 2
SRE_INFO_CHARSET = 4
SRE_FLAG_LOCALE = 4 # honour system locale
SRE_FLAG_UNICODE = 32 # use unicode locale

