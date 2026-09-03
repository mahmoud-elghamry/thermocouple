#ifndef HAL_TEMPERATURE_BANK_H
#define HAL_TEMPERATURE_BANK_H

#include "hal/temperature_sensor.h"

#include <stdbool.h>
#include <stdint.h>

#define HAL_TEMPERATURE_BANK_CHANNELS 8u

bool hal_temperature_bank_init(void);
hal_temperature_sample_t hal_temperature_bank_read(uint8_t channel);

#endif
