#ifndef HAL_ALARM_OUTPUT_H
#define HAL_ALARM_OUTPUT_H

#include <stdbool.h>

/* Drives the status LED and the relay-driver transistor from PB3 / DIP pin 4. */
void hal_alarm_output_init(void);
void hal_alarm_output_set(bool on);
bool hal_alarm_output_is_on(void);

#endif
