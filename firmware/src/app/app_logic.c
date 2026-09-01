#include "app/app_logic.h"
#include "app/app_config.h"

#include <stddef.h>
#include <stdint.h>

bool app_alarm_next_state(bool currently_on,
                          const hal_temperature_sample_t *sample)
{
    if (sample == NULL || !sample->valid) {
        return APP_ALARM_ON_SENSOR_FAULT != 0u;
    }
    if (!currently_on && sample->temperature_x10 >= APP_ALARM_ON_TEMP_X10) {
        return true;
    }
    if (currently_on && sample->temperature_x10 <= APP_ALARM_OFF_TEMP_X10) {
        return false;
    }
    return currently_on;
}

void app_format_temperature(char out[17],
                            const hal_temperature_sample_t *sample)
{
    uint16_t magnitude;
    uint16_t whole;
    uint8_t decimal;
    uint8_t index;

    if (out == NULL) {
        return;
    }
    if (sample == NULL || !sample->valid) {
        static const char invalid_text[17] = "Temp: INVALID   ";
        for (index = 0u; index < 17u; ++index) {
            out[index] = invalid_text[index];
        }
        return;
    }

    out[0] = 'T';
    out[1] = 'e';
    out[2] = 'm';
    out[3] = 'p';
    out[4] = ':';
    out[5] = ' ';

    if (sample->temperature_x10 < 0) {
        out[6] = '-';
        magnitude = (uint16_t)(-(int32_t)sample->temperature_x10);
    } else {
        out[6] = '+';
        magnitude = (uint16_t)sample->temperature_x10;
    }

    whole = magnitude / 10u;
    decimal = (uint8_t)(magnitude % 10u);
    out[7] = (whole >= 1000u) ? (char)('0' + ((whole / 1000u) % 10u)) : ' ';
    out[8] = (whole >= 100u) ? (char)('0' + ((whole / 100u) % 10u)) : ' ';
    out[9] = (whole >= 10u) ? (char)('0' + ((whole / 10u) % 10u)) : ' ';
    out[10] = (char)('0' + (whole % 10u));
    out[11] = '.';
    out[12] = (char)('0' + decimal);
    /* HD44780 degree glyph byte 0xDF, represented as signed char -33. */
    out[13] = (char)-33;
    out[14] = 'C';
    out[15] = ' ';
    out[16] = '\0';
}

const char *app_temperature_fault_text(uint8_t faults)
{
    if ((faults & HAL_TEMPERATURE_FAULT_INIT) != 0u) {
        return "FAULT: INIT";
    }
    if ((faults & HAL_TEMPERATURE_FAULT_COMMUNICATION) != 0u) {
        return "FAULT: SPI";
    }
    if ((faults & HAL_TEMPERATURE_FAULT_OPEN) != 0u) {
        return "FAULT: OPEN";
    }
    if ((faults & HAL_TEMPERATURE_FAULT_VOLTAGE) != 0u) {
        return "FAULT: VOLTAGE";
    }
    if ((faults & HAL_TEMPERATURE_FAULT_RANGE) != 0u) {
        return "FAULT: RANGE";
    }
    if ((faults & HAL_TEMPERATURE_FAULT_THRESHOLD) != 0u) {
        return "FAULT: LIMIT";
    }
    return "Sensor: OK";
}
