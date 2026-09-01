#ifndef HAL_TEMPERATURE_SENSOR_H
#define HAL_TEMPERATURE_SENSOR_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    int16_t temperature_x10;
    bool fault;
    const char *status_text;
} hal_temperature_sample_t;

/* The build links exactly one backend: MAX6675 or MAX31856. */
void hal_temperature_sensor_init(void);
hal_temperature_sample_t hal_temperature_sensor_read(void);
const char *hal_temperature_sensor_name(void);

#endif
