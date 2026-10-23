#ifndef FAMILY_STACK_MONITOR_H
#define FAMILY_STACK_MONITOR_H
#include "common/types.h"
/* AVR startup paints unused SRAM before C initialization. Main examines at
 * most 16 bytes/pass; the getter is the largest observed overwrite depth. */
void app_stack_step(void);
uint16_t app_stack_highwater(void);
#ifdef FAMILY_REGISTER_MODEL
uint16_t app_stack_capacity(void);
void app_stack_refresh(void);
#endif
#endif
