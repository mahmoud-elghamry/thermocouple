#ifndef APP_PROTECTION_H
#define APP_PROTECTION_H

#include "hal/temperature_sensor.h"

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    APP_TRIP_CAUSE_NONE = 0,
    APP_TRIP_CAUSE_TEMPERATURE,
    APP_TRIP_CAUSE_SENSOR_FAULT
} app_trip_cause_t;

typedef struct {
    bool latched;
    uint8_t first_channel;
    app_trip_cause_t cause;
} app_protection_state_t;

void app_protection_reset(app_protection_state_t *state);
void app_protection_evaluate(app_protection_state_t *state,
                             const hal_temperature_sample_t *samples,
                             uint8_t count,
                             int16_t trip_temperature_x10);
bool app_protection_try_ack(app_protection_state_t *state,
                            const hal_temperature_sample_t *samples,
                            uint8_t count,
                            int16_t reset_temperature_x10);
bool app_protection_run_permitted(const app_protection_state_t *state);
bool app_protection_output_permitted(bool first_scan_done,
                                     const app_protection_state_t *state);
void app_format_channel_line(char out[17],
                             uint8_t channel,
                             const hal_temperature_sample_t *sample);

#endif
