#include "app/app_config.h"
#include "app/app_logic.h"
#include "hal/alarm_output.h"
#include "hal/lcd.h"
#include "hal/temperature_sensor.h"

#include <avr/io.h>
#include <avr/wdt.h>
#include <stdbool.h>
#include <stdint.h>
#include <util/delay.h>

int main(void)
{
    char temperature_text[17];
    bool sensor_ready;

    /* A watchdog reset may leave the watchdog active.  Disable it before
       initialization, then enable the deliberate 2 s supervision below. */
    MCUSR = 0u;
    wdt_disable();

    hal_alarm_output_init();
    hal_lcd_init();
    hal_lcd_print_line(0u, "Thermocouple K");
    hal_lcd_print_line(1u, hal_temperature_sensor_name());

    sensor_ready = hal_temperature_sensor_init();
    _delay_ms(250);
    wdt_enable(WDTO_2S);

    for (;;) {
        hal_temperature_sample_t sample;

        wdt_reset();
        if (sensor_ready) {
            sample = hal_temperature_sensor_read();
            if ((sample.faults & HAL_TEMPERATURE_FAULT_COMMUNICATION) != 0u) {
                sensor_ready = false;
            }
        } else {
            sample.temperature_x10 = 0;
            sample.faults = HAL_TEMPERATURE_FAULT_INIT;
            sample.valid = false;
            sensor_ready = hal_temperature_sensor_init();
        }

        hal_alarm_output_set(app_alarm_next_state(
            hal_alarm_output_is_on(), &sample));
        app_format_temperature(temperature_text, &sample);
        hal_lcd_print_line(0u, temperature_text);

        if (!sample.valid) {
            hal_lcd_print_line(1u,
                               app_temperature_fault_text(sample.faults));
        } else if (hal_alarm_output_is_on()) {
            hal_lcd_print_line(1u, "OUTPUT: ON >=100");
        } else {
            hal_lcd_print_line(1u, "OUTPUT: OFF");
        }

        _delay_ms(500);
    }
}
