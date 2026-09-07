#include "app/protection.h"

#include <stddef.h>
#include <stdint.h>

static void write_word(char *out, const char *word, uint8_t length)
{
    uint8_t index;

    for (index = 0u; index < length; ++index) {
        out[index] = word[index];
    }
}

/* Five characters at out[11..15].  Ordered by what an operator most needs to
   know first: a blind channel outranks a range complaint. */
static void write_fault_word(char out[17], uint8_t faults)
{
    const char *word = "FAULT";

    if ((faults & HAL_TEMPERATURE_FAULT_OPEN) != 0u) {
        word = "OPEN ";
    } else if ((faults & HAL_TEMPERATURE_FAULT_COMMUNICATION) != 0u) {
        word = "SPI  ";
    } else if ((faults & HAL_TEMPERATURE_FAULT_STUCK) != 0u) {
        word = "STUCK";
    } else if ((faults & HAL_TEMPERATURE_FAULT_RATE) != 0u) {
        word = "RATE ";
    } else if ((faults & HAL_TEMPERATURE_FAULT_RANGE) != 0u) {
        word = "RANGE";
    }
    write_word(&out[11], word, 5u);
}

void app_protection_reset(app_protection_state_t *state)
{
    if (state == NULL) {
        return;
    }
    state->latched = false;
    state->config_locked = false;
    state->save_fault_recovered = false;
    state->first_channel = 0u;
    state->cause = APP_TRIP_CAUSE_NONE;
}

void app_protection_config_lock(app_protection_state_t *state)
{
    if (state == NULL) {
        return;
    }
    state->config_locked = true;
    state->latched = true;
    state->first_channel = 0u;
    state->cause = APP_TRIP_CAUSE_CONFIG;
}

void app_protection_config_unlock(app_protection_state_t *state)
{
    if (state == NULL) {
        return;
    }
    state->config_locked = false;
}

void app_protection_note_drive_fault(app_protection_state_t *state)
{
    if (state == NULL) {
        return;
    }
    /* A drive fault outranks whatever is already latched: it says the unit
       cannot stop the machine at all, which the operator has to see. */
    state->latched = true;
    state->cause = APP_TRIP_CAUSE_DRIVE;
}

void app_protection_note_save_fault(app_protection_state_t *state)
{
    if (state == NULL) {
        return;
    }
    /* A trip already showing for any other reason outranks a save failure:
       a temperature, sensor or drive fault must stay visible, not be
       replaced by an operator's rejected edit (I-036). */
    if (state->latched && state->cause != APP_TRIP_CAUSE_SAVE_FAILED) {
        return;
    }
    state->latched = true;
    state->cause = APP_TRIP_CAUSE_SAVE_FAILED;
    state->save_fault_recovered = false;
    state->first_channel = 0u;
}

void app_protection_note_save_recovered(app_protection_state_t *state)
{
    if (state == NULL) {
        return;
    }
    if (state->cause == APP_TRIP_CAUSE_SAVE_FAILED) {
        state->save_fault_recovered = true;
    }
}

void app_protection_evaluate(app_protection_state_t *state,
                             const hal_temperature_sample_t *samples,
                             uint8_t count,
                             int16_t trip_temperature_x10)
{
    uint8_t channel;

    if (state == NULL || state->latched) {
        return;
    }
    if (samples == NULL || count == 0u) {
        state->latched = true;
        state->first_channel = 0u;
        state->cause = APP_TRIP_CAUSE_SENSOR_FAULT;
        return;
    }

    for (channel = 0u; channel < count; ++channel) {
        if (!samples[channel].valid) {
            state->latched = true;
            state->first_channel = channel;
            state->cause = APP_TRIP_CAUSE_SENSOR_FAULT;
            return;
        }
        if (samples[channel].temperature_x10 >= trip_temperature_x10) {
            state->latched = true;
            state->first_channel = channel;
            state->cause = APP_TRIP_CAUSE_TEMPERATURE;
            return;
        }
    }
}

bool app_protection_try_ack(app_protection_state_t *state,
                            const hal_temperature_sample_t *samples,
                            uint8_t count,
                            int16_t reset_temperature_x10)
{
    uint8_t channel;

    if (state == NULL || samples == NULL || count == 0u) {
        return false;
    }
    /* No setpoint, no acknowledgement.  Otherwise a blank unit could be
       cleared straight into permitting the machine to run. */
    if (state->config_locked) {
        return false;
    }
    /* A drive fault is not the operator's to clear: the hardware has to be
       repaired and the unit power-cycled. */
    if (state->cause == APP_TRIP_CAUSE_DRIVE) {
        return false;
    }
    /* A save failure has nothing to do with temperature, so it is cleared on
       its own condition: a retry must have succeeded first (I-036). */
    if (state->cause == APP_TRIP_CAUSE_SAVE_FAILED) {
        if (!state->save_fault_recovered) {
            return false;
        }
        app_protection_reset(state);
        return true;
    }
    for (channel = 0u; channel < count; ++channel) {
        if (!samples[channel].valid ||
            samples[channel].temperature_x10 > reset_temperature_x10) {
            return false;
        }
    }
    app_protection_reset(state);
    return true;
}

bool app_protection_run_permitted(const app_protection_state_t *state)
{
    return state != NULL && !state->latched;
}

bool app_protection_output_permitted(bool first_scan_done,
                                     const app_protection_state_t *state)
{
    return first_scan_done && app_protection_run_permitted(state);
}

void app_format_channel_line(char out[17],
                             uint8_t channel,
                             const hal_temperature_sample_t *sample)
{
    uint16_t magnitude;
    uint16_t whole;
    uint8_t decimal;

    if (out == NULL) {
        return;
    }

    out[0] = 'C';
    out[1] = 'H';
    out[2] = (char)('1' + channel);
    out[3] = ':';

    if (sample == NULL || !sample->valid) {
        out[4] = '-';
        out[5] = '-';
        out[6] = '-';
        out[7] = '.';
        out[8] = '-';
        out[9] = 'C';
        out[10] = ' ';
        write_fault_word(out, sample == NULL ? HAL_TEMPERATURE_FAULT_INIT
                                              : sample->faults);
        out[16] = '\0';
        return;
    }

    if (sample->temperature_x10 < 0) {
        out[4] = '-';
        magnitude = (uint16_t)(-(int32_t)sample->temperature_x10);
    } else {
        out[4] = '+';
        magnitude = (uint16_t)sample->temperature_x10;
    }
    whole = magnitude / 10u;
    decimal = (uint8_t)(magnitude % 10u);
    out[5] = (whole >= 1000u) ? (char)('0' + ((whole / 1000u) % 10u)) : ' ';
    out[6] = (whole >= 100u) ? (char)('0' + ((whole / 100u) % 10u)) : ' ';
    out[7] = (whole >= 10u) ? (char)('0' + ((whole / 10u) % 10u)) : ' ';
    out[8] = (char)('0' + (whole % 10u));
    out[9] = '.';
    out[10] = (char)('0' + decimal);
    out[11] = (char)-33;
    out[12] = 'C';
    out[13] = ' ';
    out[14] = 'O';
    out[15] = 'K';
    out[16] = '\0';
}

void app_format_status_line(char out[17],
                            const app_protection_state_t *state,
                            int16_t setpoint_x10,
                            bool editing)
{
    uint16_t whole;
    uint8_t digit_start;
    uint8_t index;

    if (out == NULL || state == NULL) {
        return;
    }
    whole = (setpoint_x10 < 0) ? 0u : (uint16_t)((uint16_t)setpoint_x10 / 10u);

    for (index = 0u; index < 16u; ++index) {
        out[index] = ' ';
    }
    out[16] = '\0';

    /* The candidate value being entered must always be visible, even on a
       blank unit (config_locked) or while a save-failure trip is waiting on
       a retry - those are the only two latched causes editing is allowed to
       start from (I-037).  The caller only opens editing under one of those
       two conditions or with nothing latched at all, and closes it the
       moment a temperature, sensor or drive trip latches, so this ordering
       can never hide one of those behind the edit screen. */
    if (editing) {
        write_word(&out[0], "EDIT", 4u);
        write_word(&out[5], "SP:", 3u);
        digit_start = 8u;
    } else if (state->config_locked) {
        /* A unit with no stored setpoint tells the operator what to do about
           it rather than showing a trip they cannot clear. */
        write_word(&out[0], "SET SETPOINT", 12u);
        return;
    } else if (state->latched) {
        switch (state->cause) {
        case APP_TRIP_CAUSE_DRIVE:
            write_word(&out[0], "TRIP RELAY FAIL", 15u);
            return;
        case APP_TRIP_CAUSE_TEMPERATURE:
            write_word(&out[0], "TRIP CH", 7u);
            out[7] = (char)('1' + state->first_channel);
            write_word(&out[9], "TEMP", 4u);
            return;
        case APP_TRIP_CAUSE_SAVE_FAILED:
            /* Same wording whether the save just failed or a retry has since
               succeeded and is waiting on ACK - only the second word differs,
               so a partial read of the display cannot mistake one for the
               other. */
            write_word(&out[0],
                       state->save_fault_recovered ? "SAVE OK ACK"
                                                    : "SAVE FAILED",
                       11u);
            return;
        case APP_TRIP_CAUSE_CONFIG:
            /* Reachable only after a first-time save has succeeded and
               lifted config_locked: the value is stored, but the trip still
               needs the same acknowledgement as any other. */
            write_word(&out[0], "SAVE OK ACK", 11u);
            return;
        default:
            write_word(&out[0], "TRIP CH", 7u);
            out[7] = (char)('1' + state->first_channel);
            write_word(&out[9], "FAULT", 5u);
            return;
        }
    } else {
        write_word(&out[0], "SP:", 3u);
        digit_start = 3u;
        write_word(&out[11], "SAFE", 4u);
    }
    out[digit_start] = (whole >= 1000u)
                           ? (char)('0' + ((whole / 1000u) % 10u))
                           : ' ';
    out[digit_start + 1u] = (whole >= 100u)
                                ? (char)('0' + ((whole / 100u) % 10u))
                                : ' ';
    out[digit_start + 2u] = (whole >= 10u)
                                ? (char)('0' + ((whole / 10u) % 10u))
                                : ' ';
    out[digit_start + 3u] = (char)('0' + (whole % 10u));
    out[digit_start + 4u] = (char)-33;
    out[digit_start + 5u] = 'C';
}
