#ifndef APP_PROTECTION_H
#define APP_PROTECTION_H

#include "hal/temperature_sensor.h"

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    APP_TRIP_CAUSE_NONE = 0,
    APP_TRIP_CAUSE_TEMPERATURE,
    APP_TRIP_CAUSE_SENSOR_FAULT,
    /* No usable setpoint in EEPROM.  Not a temperature event: the unit does
       not know what it is protecting against, so it protects against
       everything and refuses to permit running (I-012). */
    APP_TRIP_CAUSE_CONFIG,
    /* The run-permit read-back disagreed with the pin: stuck output, open
       coil or failed transistor.  The unit can no longer prove it is able to
       stop the machine (I-016). */
    APP_TRIP_CAUSE_DRIVE,
    /* A candidate setpoint failed to persist (EEPROM write or read-back
       mismatch).  The previously active setpoint is unaffected - this cause
       only exists to make the failure visible and stop the unit until an
       operator has both retried it successfully and acknowledged the
       recovery (I-036). */
    APP_TRIP_CAUSE_SAVE_FAILED
} app_trip_cause_t;

typedef struct {
    bool latched;
    /* While set, no acknowledgement can clear the latch.  Only storing a
       valid setpoint lifts it. */
    bool config_locked;
    /* Set once a save that failed has since been retried successfully.
       Meaningful only while cause == APP_TRIP_CAUSE_SAVE_FAILED: it is what
       app_protection_try_ack() requires before it will clear the trip
       (I-036). */
    bool save_fault_recovered;
    uint8_t first_channel;
    app_trip_cause_t cause;
} app_protection_state_t;

void app_protection_reset(app_protection_state_t *state);

/* Latches a config trip and blocks acknowledgement until a setpoint is
   stored.  Called at boot when the EEPROM record does not validate. */
void app_protection_config_lock(app_protection_state_t *state);

/* Lifts the config lock after a setpoint has been written successfully.  The
   trip itself still has to be acknowledged. */
void app_protection_config_unlock(app_protection_state_t *state);

/* Latches a drive-fault trip.  Idempotent. */
void app_protection_note_drive_fault(app_protection_state_t *state);

/* Latches a save-failure trip: a candidate setpoint was rejected by
   persistence (I-036).  A no-op if a higher-priority trip (temperature,
   sensor fault, config or drive) is already showing, so editing or saving
   can never erase a safety trip that is already latched. */
void app_protection_note_save_fault(app_protection_state_t *state);

/* Marks a save-failure trip as resolved by a successful retry.  Does not
   itself clear the latch - app_protection_try_ack() still requires an
   explicit acknowledgement (I-036). */
void app_protection_note_save_recovered(app_protection_state_t *state);

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
void app_format_status_line(char out[17],
                            const app_protection_state_t *state,
                            int16_t setpoint_x10,
                            bool editing);

#endif
