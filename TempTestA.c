#include "Platform_Types.h"
#include "Std_Types.h"
#include "Rte.h"

Std_ReturnType Add(uint32 a, uint32 b, uint32* result) {

    if (result == (void *)0) {
        return E_NOT_OK;
    }

    *result = a + b;
    return E_OK;
}

uint32 TempA(void) {

    uint32 num1 = 5;
    uint32 num2 = 7;
    uint32 sum = 0;

    Std_ReturnType addResult = Add(num1, num2, &sum);

    return 0;
}
