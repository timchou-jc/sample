/* Support for restrict added to QAC 9.1.0 onwards */
#if __QAC_MAJOR__ < 91
#  define restrict
#else
#  define restrict restrict
#endif

#define __restrict restrict
#define __restrict__ restrict
