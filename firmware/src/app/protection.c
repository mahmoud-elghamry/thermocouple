#include "app/protection.h"

#include <stddef.h>
#include <stdint.h>

static void write_fault_word(char out[17], uint8_t faults)
{
    const char *word = "FAULT";
    uint8_t index;

    if ((faults & HAL_TEMPERATURE_FAULT_OPEN) != 0u) {
        word = "OPEN ";
    } else if ((faults & HAL_TEMPERATURE_FAULT_COMMUNICATION) != 0u) {
        word = "SPI  ";
    } else if ((faults & HAL_TEMPERATURE_FAULT_RANGE) != 0u) {
        word = "RANGE";
    }
    for (index = 0u; index < 5u; ++index) {
        out[11u + index] = word[index];
    }
}

void app_protection_reset(app_protection_state_t *state)
{
    if (state == NULL) {
        return;
    }
    state->latched = false;
    state->first_channel = 0u;
    state->cause = APP_TRIP_CAUSE_NONE;
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
