#include "app/app_config.h"
#include "hal/alarm_output.h"
#include "hal/lcd.h"
#include "hal/temperature_sensor.h"

#include <stdbool.h>
#include <stdint.h>
#include <util/delay.h>

static void format_temperature(char out[17], int16_t temperature_x10)
{
    uint16_t magnitude;
    uint16_t whole;
    uint8_t decimal;

    out[0] = 'T';
    out[1] = 'e';
    out[2] = 'm';
    out[3] = 'p';
    out[4] = ':';
    out[5] = ' ';

    if (temperature_x10 < 0) {
        out[6] = '-';
        magnitude = (uint16_t)(-temperature_x10);
    } else {
        out[6] = '+';
        magnitude = (uint16_t)temperature_x10;
    }

    whole = magnitude / 10u;
    decimal = (uint8_t)(magnitude % 10u);
    out[7] = (whole >= 1000u) ? (char)('0' + ((whole / 1000u) % 10u)) : ' ';
    out[8] = (whole >= 100u) ? (char)('0' + ((whole / 100u) % 10u)) : ' ';
    out[9] = (whole >= 10u) ? (char)('0' + ((whole / 10u) % 10u)) : ' ';
    out[10] = (char)('0' + (whole % 10u));
    out[11] = '.';
    out[12] = (char)('0' + decimal);
    out[13] = (char)0xDF;
    out[14] = 'C';
    out[15] = ' ';
    out[16] = '\0';
}

static void update_alarm(const hal_temperature_sample_t *sample)
{
    bool alarm_on = hal_alarm_output_is_on();

    if (sample->fault) {
        alarm_on = false;
    } else if (!alarm_on && sample->temperature_x10 >= APP_ALARM_ON_TEMP_X10) {
        alarm_on = true;
    } else if (alarm_on && sample->temperature_x10 <= APP_ALARM_OFF_TEMP_X10) {
        alarm_on = false;
    }

    hal_alarm_output_set(alarm_on);
}

int main(void)
{
    char temperature_text[17];

    hal_alarm_output_init();
    hal_lcd_init();
    hal_lcd_print_line(0u, "Thermocouple K");
    hal_lcd_print_line(1u, hal_temperature_sensor_name());

    hal_temperature_sensor_init();
    _delay_ms(250);

    for (;;) {
        hal_temperature_sample_t sample = hal_temperature_sensor_read();

        update_alarm(&sample);
        format_temperature(temperature_text, sample.temperature_x10);
        hal_lcd_print_line(0u, temperature_text);

        if (sample.fault) {
            hal_lcd_print_line(1u, sample.status_text);
        } else if (hal_alarm_output_is_on()) {
            hal_lcd_print_line(1u, "OUTPUT: ON >=100");
        } else {
            hal_lcd_print_line(1u, "OUTPUT: OFF");
        }

        _delay_ms(500);
    }
}
