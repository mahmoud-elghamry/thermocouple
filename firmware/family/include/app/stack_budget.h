#ifndef FAMILY_STACK_BUDGET_H
#define FAMILY_STACK_BUDGET_H
/* avr-gcc -Os settings_commit frame = 1046 B, before its callers/interrupts.
 * Shared with build.ps1's RAM and frame gates; total budget remains 12 KiB. */
#define APP_STACK_BYTES 1536u
#endif
