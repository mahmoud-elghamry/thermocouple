#ifndef HAL_TEMPERATURE_SENSOR_H
#define HAL_TEMPERATURE_SENSOR_H

#include <stdbool.h>
#include <stdint.h>

#define HAL_TEMPERATURE_FAULT_NONE          0x00u
#define HAL_TEMPERATURE_FAULT_OPEN          0x01u
#define HAL_TEMPERATURE_FAULT_VOLTAGE       0x02u
#define HAL_TEMPERATURE_FAULT_RANGE         0x04u
#define HAL_TEMPERATURE_FAULT_THRESHOLD     0x08u
#define HAL_TEMPERATURE_FAULT_COMMUNICATION 0x10u
#define HAL_TEMPERATURE_FAULT_INIT          0x20u

typedef struct {
    int16_t temperature_x10;
    uint8_t faults;
    bool valid;
} hal_temperature_sample_t;

/* The build links exactly one backend: MAX6675 or MAX31856. */
bool hal_temperature_sensor_init(void);
hal_temperature_sample_t hal_temperature_sensor_read(void);
const char *hal_temperature_sensor_name(void);

#endif
