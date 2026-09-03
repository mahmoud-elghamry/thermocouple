#include "app/app_config.h"
#include "app/protection.h"
#include "hal/alarm_output.h"
#include "hal/buttons.h"
#include "hal/lcd.h"
#include "hal/temperature_bank.h"

#include <avr/io.h>
#include <avr/wdt.h>
#include <stdbool.h>
#include <stdint.h>
#include <util/delay.h>

#define SENSOR_SCAN_TICKS        10u
#define AUTO_PAGE_TICKS          40u

static hal_temperature_sample_t samples[HAL_TEMPERATURE_BANK_CHANNELS];

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
}

static void format_status_line(char out[17],
                               const app_protection_state_t *protection,
                               int16_t setpoint_x10,
                               bool editing)
{
    uint16_t whole = (uint16_t)setpoint_x10 / 10u;
    uint8_t digit_start;
    uint8_t index;

    for (index = 0u; index < 16u; ++index) {
        out[index] = ' ';
    }
    out[16] = '\0';

    if (protection->latched) {
        out[0] = 'T'; out[1] = 'R'; out[2] = 'I'; out[3] = 'P';
        out[4] = ' ';
        out[5] = 'C'; out[6] = 'H';
        out[7] = (char)('1' + protection->first_channel);
        out[8] = ' ';
        if (protection->cause == APP_TRIP_CAUSE_TEMPERATURE) {
            out[9] = 'T'; out[10] = 'E'; out[11] = 'M'; out[12] = 'P';
        } else {
            out[9] = 'F'; out[10] = 'A'; out[11] = 'U'; out[12] = 'L';
            out[13] = 'T';
        }
        return;
    }

    if (editing) {
        out[0] = 'E'; out[1] = 'D'; out[2] = 'I'; out[3] = 'T';
        out[5] = 'S'; out[6] = 'P'; out[7] = ':';
        digit_start = 8u;
    } else {
        out[0] = 'S'; out[1] = 'P'; out[2] = ':';
        digit_start = 3u;
        out[11] = 'S'; out[12] = 'A'; out[13] = 'F'; out[14] = 'E';
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

int main(void)
{
    app_protection_state_t protection;
    char lcd_line[17];
    int16_t setpoint_x10 = APP_8CH_DEFAULT_TRIP_TEMP_X10;
    uint8_t selected_channel = 0u;
    uint8_t scan_ticks = 0u;
    uint8_t page_ticks = 0u;
    bool editing = false;
    bool first_scan_done = false;

    MCUSR = 0u;
    wdt_disable();

    hal_alarm_output_init();
    hal_buttons_init();
    hal_lcd_init();
    initialize_samples();
    app_protection_reset(&protection);

    hal_lcd_print_line(0u, "8CH MAX6675");
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
        if ((events & HAL_BUTTON_EVENT_SET) != 0u && !protection.latched) {
            editing = !editing;
        }
        if (editing && !protection.latched &&
            (events & HAL_BUTTON_EVENT_UP) != 0u &&
            setpoint_x10 <= (APP_8CH_MAX_SETPOINT_X10 -
                             APP_8CH_SETPOINT_STEP_X10)) {
            setpoint_x10 += APP_8CH_SETPOINT_STEP_X10;
        }
        if (editing && !protection.latched &&
            (events & HAL_BUTTON_EVENT_DOWN) != 0u &&
            setpoint_x10 >= (APP_8CH_MIN_SETPOINT_X10 +
                             APP_8CH_SETPOINT_STEP_X10)) {
            setpoint_x10 -= APP_8CH_SETPOINT_STEP_X10;
        }
        if ((events & HAL_BUTTON_EVENT_ACK) != 0u) {
            int16_t reset_temperature_x10 =
                (setpoint_x10 >= APP_8CH_HYSTERESIS_X10)
                    ? (int16_t)(setpoint_x10 - APP_8CH_HYSTERESIS_X10)
                    : setpoint_x10;

            (void)app_protection_try_ack(&protection,
                                         samples,
                                         HAL_TEMPERATURE_BANK_CHANNELS,
                                         reset_temperature_x10);
        }

        ++scan_ticks;
        if (scan_ticks >= SENSOR_SCAN_TICKS) {
            scan_ticks = 0u;
            read_all_channels();
            first_scan_done = true;
            app_protection_evaluate(&protection,
                                    samples,
                                    HAL_TEMPERATURE_BANK_CHANNELS,
                                    setpoint_x10);
            if (protection.latched) {
                editing = false;
            }
        }

        if (!editing) {
            ++page_ticks;
            if (page_ticks >= AUTO_PAGE_TICKS) {
                page_ticks = 0u;
                selected_channel = (uint8_t)((selected_channel + 1u) %
                                             HAL_TEMPERATURE_BANK_CHANNELS);
            }
        }

        /* Energized-to-run: power loss, boot, fault or trip removes permit. */
        hal_alarm_output_set(app_protection_output_permitted(first_scan_done,
                                                              &protection));

        app_format_channel_line(lcd_line,
                                selected_channel,
                                &samples[selected_channel]);
        hal_lcd_print_line(0u, lcd_line);
        format_status_line(lcd_line, &protection, setpoint_x10, editing);
        hal_lcd_print_line(1u, lcd_line);

        _delay_ms(50);
    }
}
