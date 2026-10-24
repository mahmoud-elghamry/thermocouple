#include "core_test.h"
unsigned checks, failures;
int main(void)
{
    test_settings(); test_events(); test_fault(); test_channel();
    test_protection(); test_outputs(); test_tc_math(); test_scenarios();
    printf("Lane B: %u checks, %u failures\n",checks,failures);
    return failures ? 1 : 0;
}
