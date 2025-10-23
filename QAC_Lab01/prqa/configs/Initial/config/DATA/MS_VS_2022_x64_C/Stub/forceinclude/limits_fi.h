#define CHAR_BIT      8
#define SCHAR_MIN   (-128)
#define SCHAR_MAX     127
#define UCHAR_MAX     0xff

#ifndef _CHAR_UNSIGNED
    #define CHAR_MIN    SCHAR_MIN
    #define CHAR_MAX    SCHAR_MAX
#else
    #define CHAR_MIN    0
    #define CHAR_MAX    UCHAR_MAX
#endif

#define MB_LEN_MAX    5
#define SHRT_MIN    (-32768)
#define SHRT_MAX      32767
#define USHRT_MAX     0xffff

#define INT_MIN     (-2147483647 - 1)
#define INT_MAX       2147483647
#define UINT_MAX      0xffffffff

#define LONG_MIN    (-2147483647L - 1)
#define LONG_MAX      2147483647L
#define ULONG_MAX     0xffffffffUL

#define LLONG_MIN   (-9223372036854775807LL-1LL)
#define LLONG_MAX     9223372036854775807LL
#define ULLONG_MAX    0xffffffffffffffffULL

#define _I8_MIN     (-128)
#define _I8_MAX       127
#define _UI8_MAX      0xff

#define _I16_MIN    (-32768)
#define _I16_MAX      32767
#define _UI16_MAX     0xffff

#define _I32_MIN    (-2147483647 - 1)
#define _I32_MAX      2147483647
#define _UI32_MAX     0xffffffffUL

#define _I64_MIN    (-9223372036854775807LL-1LL)
#define _I64_MAX      9223372036854775807LL
#define _UI64_MAX     0xffffffffffffffffULL
