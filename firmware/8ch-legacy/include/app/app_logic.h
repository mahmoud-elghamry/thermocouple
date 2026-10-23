#ifndef APP_LOGIC_H
#define APP_LOGIC_H

#include "hal/temperature_sensor.h"

#include <stdbool.h>
#include <stdint.h>

bool app_alarm_next_state(bool currently_on,
                          const hal_temperature_sample_t *sample);
void app_format_temperature(char out[17],
                            const hal_temperature_sample_t *sample);
const char *app_temperature_fault_text(uint8_t faults);

#endif
