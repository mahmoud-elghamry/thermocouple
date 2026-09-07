/* Eight-channel thermocouple protection unit - THERMO-8CH REV A0.
 *
 * Energised to run.  PB3 is HIGH only while the unit has scanned all eight
 * channels, every reading is trusted, a setpoint is stored, and none of the
 * channels is at or above it.  Power loss, reset, watchdog, a sensor fault, a
 * blank EEPROM or a trip all drop the pin, R31 pulls the gate down and the
 * dry contact opens.
 */

#include "app/app_config.h"
#include "app/protection.h"
#include "app/sensor_monitor.h"
#include "app/settings.h"
#include "app/version.h"
#include "hal/buttons.h"
#include "hal/lcd.h"
#include "hal/run_permit.h"
#include "hal/settings_store.h"
#include "hal/temperature_bank.h"

#include <avr/io.h>
#include <avr/wdt.h>
#include <stdbool.h>
#include <stdint.h>
#include <util/delay.h>

static hal_temperature_sample_t samples[HAL_TEMPERATURE_BANK_CHANNELS];
static app_sensor_monitor_t monitor;

static void initialize_samples(void)
{
    uint8_t channel;

    for (channel = 0u; channel < HAL_TEMPERATURE_BANK_CHANNELS; ++channel) {
        samples[channel].temperature_x10 = 0;
        samples[channel].faults = HAL_TEMPERATURE_FAULT_INIT;
        samples[channel].valid = false;
    }
}

static void read_all_channels(void)
{
    uint8_t channel;

    for (channel = 0u; channel < HAL_TEMPERATURE_BANK_CHANNELS; ++channel) {
        samples[channel] = hal_temperature_bank_read(channel);
    }
    app_sensor_monitor_update(&monitor, samples,
                              HAL_TEMPERATURE_BANK_CHANNELS);
}

/* Stores the setpoint and lifts the config lock.  A write that cannot be read
   back is not a stored setpoint, so the lock stays on.  The caller decides
   what a false return means for the active setpoint - this function never
   touches it (I-036). */
static bool persist_setpoint(app_protection_state_t *protection,
                             int16_t setpoint_x10)
{
    app_settings_t record;

    app_settings_build(&record, setpoint_x10);
    if (!hal_settings_store_save(&record)) {
        return false;
    }
    app_protection_config_unlock(protection);
    app_protection_note_save_recovered(protection);
    return true;
}

int main(void)
{
    app_protection_state_t protection;
    app_settings_t settings;
    char lcd_line[17];
    /* active_setpoint_x10 is the only value protection ever evaluates
       against.  UP/DOWN never touch it - they touch candidate_setpoint_x10,
       which is promoted to active only after a successful, read-back-verified
       EEPROM save (I-036). */
    int16_t active_setpoint_x10;
    int16_t candidate_setpoint_x10;
    uint8_t selected_channel = 0u;
    uint8_t scan_ticks = 0u;
    uint8_t page_ticks = 0u;
    uint8_t drive_mismatch_scans = 0u;
    bool editing = false;
    bool first_scan_done = false;
    bool setpoint_stored;

    /* A watchdog reset may leave the watchdog running.  Disable it before
       initialization, then enable the deliberate 2 s supervision below. */
    MCUSR = 0u;
    wdt_disable();

    hal_run_permit_init();
    hal_buttons_init();
    hal_lcd_init();
    initialize_samples();
    app_sensor_monitor_reset(&monitor);
    app_protection_reset(&protection);

    hal_lcd_print_line(0u, APP_TARGET_BOARD);
    hal_lcd_print_line(1u, APP_BOOT_BANNER);
    _delay_ms(750);

    /* The setpoint comes from EEPROM or the unit does not run.  There is no
       safe hard-coded temperature for someone else's engine (R-8, I-012). */
    setpoint_stored = hal_settings_store_load(&settings);
    if (setpoint_stored) {
        active_setpoint_x10 = settings.setpoint_x10;
    } else {
        active_setpoint_x10 = APP_8CH_DEFAULT_TRIP_TEMP_X10;
        app_protection_config_lock(&protection);
    }
    candidate_setpoint_x10 = active_setpoint_x10;

    hal_lcd_print_line(0u, hal_temperature_bank_name());
    hal_lcd_print_line(1u, "Initializing...");
    (void)hal_temperature_bank_init();
    _delay_ms(250);
    wdt_enable(WDTO_2S);

    for (;;) {
        uint8_t events;

        wdt_reset();
        events = hal_buttons_poll();

        if ((events & HAL_BUTTON_EVENT_NEXT) != 0u) {
            selected_channel = (uint8_t)((selected_channel + 1u) %
                                         HAL_TEMPERATURE_BANK_CHANNELS);
            page_ticks = 0u;
        }

        /* SET enters edit mode, and leaving it is what commits the setpoint.
           Editing is allowed while config-locked or while a previous save
           has failed and not yet been acknowledged - those are the only two
           ways in that a latched unit may still open the edit screen
           (I-036, I-037). */
        if ((events & HAL_BUTTON_EVENT_SET) != 0u &&
            (!protection.latched || protection.config_locked ||
             protection.cause == APP_TRIP_CAUSE_SAVE_FAILED)) {
            if (editing) {
                editing = false;
                if (persist_setpoint(&protection, candidate_setpoint_x10)) {
                    active_setpoint_x10 = candidate_setpoint_x10;
                } else {
                    /* Discard the candidate, not the active setpoint: the
                       previously stored value keeps protecting the machine,
                       and the operator sees the failure and may retry
                       (I-036). */
                    app_protection_note_save_fault(&protection);
                }
            } else {
                candidate_setpoint_x10 = active_setpoint_x10;
                editing = true;
            }
        }
        if (editing &&
            (events & HAL_BUTTON_EVENT_UP) != 0u &&
            candidate_setpoint_x10 <= (APP_8CH_MAX_SETPOINT_X10 -
                                       APP_8CH_SETPOINT_STEP_X10)) {
            candidate_setpoint_x10 += APP_8CH_SETPOINT_STEP_X10;
        }
        if (editing &&
            (events & HAL_BUTTON_EVENT_DOWN) != 0u &&
            candidate_setpoint_x10 >= (APP_8CH_MIN_SETPOINT_X10 +
                                       APP_8CH_SETPOINT_STEP_X10)) {
            candidate_setpoint_x10 -= APP_8CH_SETPOINT_STEP_X10;
        }
        if ((events & HAL_BUTTON_EVENT_ACK) != 0u) {
            int16_t reset_temperature_x10 =
                (active_setpoint_x10 >= APP_8CH_HYSTERESIS_X10)
                    ? (int16_t)(active_setpoint_x10 - APP_8CH_HYSTERESIS_X10)
                    : active_setpoint_x10;

            (void)app_protection_try_ack(&protection,
                                         samples,
                                         HAL_TEMPERATURE_BANK_CHANNELS,
                                         reset_temperature_x10);
        }

        ++scan_ticks;
        if (scan_ticks >= APP_8CH_SCAN_TICKS) {
            scan_ticks = 0u;
            read_all_channels();
            first_scan_done = true;
            app_protection_evaluate(&protection,
                                    samples,
                                    HAL_TEMPERATURE_BANK_CHANNELS,
                                    active_setpoint_x10);
            /* A real trip closes the edit screen so it cannot hide behind
               it.  Config-lock and a pending save retry are the two states
               editing is meant to survive (I-036, I-037). */
            if (protection.latched && !protection.config_locked &&
                protection.cause != APP_TRIP_CAUSE_SAVE_FAILED) {
                editing = false;
            }

            /* Does the driver actually follow the pin?  Checked after the
               output was set at least once, and only after several
               consecutive disagreements so a relay in motion is not a
               fault.  Compiled out on REV A0 - see mcal/board.h. */
            if (first_scan_done && !hal_run_permit_readback_agrees()) {
                if (drive_mismatch_scans < APP_8CH_DRIVE_FAULT_SCANS) {
                    ++drive_mismatch_scans;
                }
                if (drive_mismatch_scans >= APP_8CH_DRIVE_FAULT_SCANS) {
                    app_protection_note_drive_fault(&protection);
                }
            } else {
                drive_mismatch_scans = 0u;
            }
        }

        if (!editing) {
            ++page_ticks;
            if (page_ticks >= APP_8CH_AUTO_PAGE_TICKS) {
                page_ticks = 0u;
                selected_channel = (uint8_t)((selected_channel + 1u) %
                                             HAL_TEMPERATURE_BANK_CHANNELS);
            }
        }

        /* Energised to run: boot, fault, missing setpoint or trip all remove
           the permit. */
        hal_run_permit_set(app_protection_output_permitted(first_scan_done,
                                                           &protection));

        app_format_channel_line(lcd_line,
                                selected_channel,
                                &samples[selected_channel]);
        hal_lcd_print_line(0u, lcd_line);
        app_format_status_line(lcd_line, &protection,
                               editing ? candidate_setpoint_x10
                                       : active_setpoint_x10,
                               editing);
        hal_lcd_print_line(1u, lcd_line);

        _delay_ms(APP_8CH_LOOP_PERIOD_MS);
    }
}
