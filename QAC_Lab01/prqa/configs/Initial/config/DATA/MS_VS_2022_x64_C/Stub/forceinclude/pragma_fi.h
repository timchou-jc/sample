/* Support for _Pragma added to QAC 9.6.0 onwards */
#if __QAC_MAJOR__ < 96
#define _Pragma _ignore_paren
#endif
