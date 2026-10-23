#ifndef APP_SENSOR_MONITOR_H
#define APP_SENSOR_MONITOR_H

#include "hal/temperature_bank.h"
#include "hal/temperature_sensor.h"

#include <stdbool.h>
#include <stdint.h>

/* Plausibility checks on top of the converter's own fault flags.
 *
 * A shorted junction reads the cold-junction temperature, forever, with no
 * fault bit set.  A frozen ADC returns its last conversion, forever, with no
 * fault bit set.  In both cases the unit looks healthy while it is blind,
 * which is the worst failure a protection device can have (I-011).
 *
 * Two independent checks catch them:
 *   stuck - the reading has not moved by one tenth of a degree in the last
 *           APP_8CH_STUCK_SCANS scans
 *   rate  - the reading jumped further in one scan than a cylinder body can
 *           physically move
 *
 * Either one marks the sample invalid, which makes the protection layer
 * latch.  This module is pure: no hardware, no AVR headers, host-tested.
 */

typedef struct {
    int16_t reference_x10;      /* last value that counted as a change */
    int16_t previous_x10;       /* value from the previous scan */
    uint16_t scans_since_change;
    bool primed;                /* a previous valid reading exists */
} app_monitor_channel_t;

typedef struct {
    app_monitor_channel_t channel[HAL_TEMPERATURE_BANK_CHANNELS];
} app_sensor_monitor_t;

void app_sensor_monitor_reset(app_sensor_monitor_t *monitor);

/* Adds HAL_TEMPERATURE_FAULT_STUCK or _RATE to any sample that fails, and
   clears its valid flag.  Samples that are already invalid are left alone
   and reset that channel's history. */
void app_sensor_monitor_update(app_sensor_monitor_t *monitor,
                               hal_temperature_sample_t *samples,
                               uint8_t count);

#endif
