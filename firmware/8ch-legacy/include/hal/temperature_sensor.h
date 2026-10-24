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
/* Plausibility faults raised by app/sensor_monitor.c, not by the converter.
   A frozen ADC or a shorted junction reads perfectly well-formed data
   forever, so the converter itself can never report these (I-011). */
#define HAL_TEMPERATURE_FAULT_STUCK         0x40u
#define HAL_TEMPERATURE_FAULT_RATE          0x80u

typedef struct {
    int16_t temperature_x10;
    uint8_t faults;
    bool valid;
} hal_temperature_sample_t;

/* Single-channel backend, used by the superseded single-channel board only.
   The eight-channel board uses hal/temperature_bank.h instead. */
bool hal_temperature_sensor_init(void);
hal_temperature_sample_t hal_temperature_sensor_read(void);
const char *hal_temperature_sensor_name(void);

#endif
