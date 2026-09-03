#include "app/app_logic.h"
#include "app/protection.h"

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

static int test_alarm_hysteresis(void)
{
    hal_temperature_sample_t sample = {
        .temperature_x10 = 999,
        .faults = HAL_TEMPERATURE_FAULT_NONE,
        .valid = true,
    };

    if (app_alarm_next_state(false, &sample)) {
        return 1;
    }
    sample.temperature_x10 = 1000;
    if (!app_alarm_next_state(false, &sample)) {
        return 2;
    }
    sample.temperature_x10 = 960;
    if (!app_alarm_next_state(true, &sample)) {
        return 3;
    }
    sample.temperature_x10 = 950;
    if (app_alarm_next_state(true, &sample)) {
        return 4;
    }
    sample.valid = false;
    sample.faults = HAL_TEMPERATURE_FAULT_OPEN;
    if (app_alarm_next_state(true, &sample)) {
        return 5;
    }
    if (app_alarm_next_state(true, NULL)) {
        return 6;
    }
    return 0;
}

static int test_temperature_format(void)
{
    char text[17];
    hal_temperature_sample_t sample = {
        .temperature_x10 = 1000,
        .faults = HAL_TEMPERATURE_FAULT_NONE,
        .valid = true,
    };

    app_format_temperature(text, &sample);
    if (text[6] != '+' || text[7] != ' ' || text[8] != '1' ||
        text[9] != '0' || text[10] != '0' || text[11] != '.' ||
        text[12] != '0' || text[16] != '\0') {
        return 10;
    }

    sample.temperature_x10 = -255;
    app_format_temperature(text, &sample);
    if (text[6] != '-' || text[9] != '2' || text[10] != '5' ||
        text[12] != '5') {
        return 11;
    }

    sample.valid = false;
    sample.faults = HAL_TEMPERATURE_FAULT_COMMUNICATION;
    app_format_temperature(text, &sample);
    if (strcmp(text, "Temp: INVALID   ") != 0) {
        return 12;
    }
    return 0;
}

static int test_fault_text(void)
{
    if (strcmp(app_temperature_fault_text(HAL_TEMPERATURE_FAULT_NONE),
               "Sensor: OK") != 0) {
        return 19;
    }
    if (strcmp(app_temperature_fault_text(HAL_TEMPERATURE_FAULT_OPEN),
               "FAULT: OPEN") != 0) {
        return 20;
    }
    if (strcmp(app_temperature_fault_text(
                   HAL_TEMPERATURE_FAULT_OPEN |
                   HAL_TEMPERATURE_FAULT_COMMUNICATION),
               "FAULT: SPI") != 0) {
        return 21;
    }
    return 0;
}

static int test_eight_channel_protection(void)
{
    app_protection_state_t state;
    hal_temperature_sample_t samples[8];
    uint8_t index;

    for (index = 0u; index < 8u; ++index) {
        samples[index].temperature_x10 = 500;
        samples[index].faults = HAL_TEMPERATURE_FAULT_NONE;
        samples[index].valid = true;
    }
    app_protection_reset(&state);
    if (app_protection_output_permitted(false, &state) ||
        !app_protection_output_permitted(true, &state)) {
        return 29;
    }
    app_protection_evaluate(&state, samples, 8u, 1000);
    if (!app_protection_run_permitted(&state)) {
        return 30;
    }

    samples[4].temperature_x10 = 1000;
    app_protection_evaluate(&state, samples, 8u, 1000);
    if (!state.latched || state.first_channel != 4u ||
        state.cause != APP_TRIP_CAUSE_TEMPERATURE ||
        app_protection_run_permitted(&state)) {
        return 31;
    }
    app_protection_evaluate(&state, samples, 8u, 2000);
    if (!state.latched) {
        return 36;
    }
    samples[4].temperature_x10 = 960;
    if (app_protection_try_ack(&state, samples, 8u, 950)) {
        return 32;
    }
    samples[4].temperature_x10 = 950;
    if (!app_protection_try_ack(&state, samples, 8u, 950) || state.latched) {
        return 33;
    }

    samples[2].valid = false;
    samples[2].faults = HAL_TEMPERATURE_FAULT_OPEN;
    app_protection_evaluate(&state, samples, 8u, 1000);
    if (!state.latched || state.first_channel != 2u ||
        state.cause != APP_TRIP_CAUSE_SENSOR_FAULT) {
        return 34;
    }
    if (app_protection_try_ack(&state, samples, 8u, 950)) {
        return 35;
    }
    app_protection_reset(&state);
    app_protection_evaluate(&state, NULL, 0u, 1000);
    if (!state.latched || state.cause != APP_TRIP_CAUSE_SENSOR_FAULT) {
        return 37;
    }
    return 0;
}

static int test_channel_format(void)
{
    char text[17];
    hal_temperature_sample_t sample = {
        .temperature_x10 = 1000,
        .faults = HAL_TEMPERATURE_FAULT_NONE,
        .valid = true,
    };

    app_format_channel_line(text, 4u, &sample);
    if (strcmp(text, "CH5:+ 100.0\337C OK") != 0) {
        return 40;
    }
    sample.valid = false;
    sample.faults = HAL_TEMPERATURE_FAULT_OPEN;
    app_format_channel_line(text, 1u, &sample);
    if (strcmp(text, "CH2:---.-C OPEN ") != 0) {
        return 41;
    }
    return 0;
}

int main(void)
{
    int result = test_alarm_hysteresis();
    if (result != 0) {
        return result;
    }
    result = test_temperature_format();
    if (result != 0) {
        return result;
    }
    result = test_fault_text();
    if (result != 0) {
        return result;
    }
    result = test_eight_channel_protection();
    if (result != 0) {
        return result;
    }
    return test_channel_format();
}
