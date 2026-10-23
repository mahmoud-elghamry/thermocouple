#ifndef HAL_TEMPERATURE_BANK_H
#define HAL_TEMPERATURE_BANK_H

#include "hal/temperature_sensor.h"

#include <stdbool.h>
#include <stdint.h>

#define HAL_TEMPERATURE_BANK_CHANNELS 8u

/* Configure every converter.  Returns true only when all eight answered and
   read their configuration back correctly.  A channel that fails is left
   marked for re-initialisation and reads as a fault until it recovers. */
bool hal_temperature_bank_init(void);

/* One channel.  Never blocks longer than the SPI timeout in mcal/spi.c. */
hal_temperature_sample_t hal_temperature_bank_read(uint8_t channel);

/* Which converter this build talks to, for the boot banner. */
const char *hal_temperature_bank_name(void);

#endif
