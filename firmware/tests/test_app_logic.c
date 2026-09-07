/* Host tests for the pure application and decoding logic.
 *
 * These modules are deliberately free of AVR headers so they can be linked
 * and run natively.  What is covered here is what neither a simulation nor a
 * bench test would catch: arithmetic that returns a plausible wrong number,
 * and safety rules that only fire in states that are hard to reach on real
 * hardware.
 *
 * Source list: firmware/sources/host_test.txt
 */

#include "app/app_config.h"
#include "app/app_logic.h"
#include "app/protection.h"
#include "app/sensor_monitor.h"
#include "app/settings.h"
#include "hal/tc_decode.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(condition)                                                      \
    do {                                                                      \
        if (!(condition)) {                                                   \
            printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #condition);       \
            ++failures;                                                       \
        }                                                                     \
    } while (0)

static hal_temperature_sample_t good(int16_t temperature_x10)
{
    hal_temperature_sample_t sample;

    sample.temperature_x10 = temperature_x10;
    sample.faults = HAL_TEMPERATURE_FAULT_NONE;
    sample.valid = true;
    return sample;
}

static void fill(hal_temperature_sample_t *samples, uint8_t count,
                 int16_t temperature_x10)
{
    uint8_t index;

    for (index = 0u; index < count; ++index) {
        samples[index] = good(temperature_x10);
    }
}

/* --- legacy single-channel logic ----------------------------------------- */

static void test_alarm_hysteresis(void)
{
    hal_temperature_sample_t sample = good(999);

    CHECK(!app_alarm_next_state(false, &sample));
    sample.temperature_x10 = 1000;
    CHECK(app_alarm_next_state(false, &sample));
    sample.temperature_x10 = 960;
    CHECK(app_alarm_next_state(true, &sample));
    sample.temperature_x10 = 950;
    CHECK(!app_alarm_next_state(true, &sample));

    sample.valid = false;
    sample.faults = HAL_TEMPERATURE_FAULT_OPEN;
    CHECK(!app_alarm_next_state(true, &sample));
    CHECK(!app_alarm_next_state(true, NULL));
}

static void test_temperature_format(void)
{
    char text[17];
    hal_temperature_sample_t sample = good(1234);

    app_format_temperature(text, &sample);
    CHECK(memcmp(text, "Temp: + 123.4", 13) == 0);

    sample.temperature_x10 = -55;
    app_format_temperature(text, &sample);
    CHECK(memcmp(text, "Temp: -   5.5", 13) == 0);

    sample.valid = false;
    app_format_temperature(text, &sample);
    CHECK(memcmp(text, "Temp: INVALID", 13) == 0);
}

static void test_fault_text(void)
{
    CHECK(strcmp(app_temperature_fault_text(HAL_TEMPERATURE_FAULT_NONE),
                 "Sensor: OK") == 0);
    CHECK(strcmp(app_temperature_fault_text(HAL_TEMPERATURE_FAULT_OPEN),
                 "FAULT: OPEN") == 0);
    CHECK(strcmp(app_temperature_fault_text(HAL_TEMPERATURE_FAULT_INIT),
                 "FAULT: INIT") == 0);
}

/* --- MAX31856 decoding (I-019) -------------------------------------------- */

/* Builds the three linearised temperature registers for a temperature, the
   way the converter presents them: signed 19-bit count of 1/128 degC, left
   aligned into bits [23:5]. */
static void encode_31856(double celsius, uint8_t out[3])
{
    long counts = (long)(celsius * 128.0);
    unsigned long reg = ((unsigned long)(counts & 0x7FFFFL) << 5) & 0xFFFFFFUL;

    out[0] = (uint8_t)((reg >> 16) & 0xFFu);
    out[1] = (uint8_t)((reg >> 8) & 0xFFu);
    out[2] = (uint8_t)(reg & 0xFFu);
}

static void test_max31856_decode(void)
{
    uint8_t data[3];

    encode_31856(0.0, data);
    CHECK(tc_max31856_decode_x10(data) == 0);

    encode_31856(25.0, data);
    CHECK(tc_max31856_decode_x10(data) == 250);

    encode_31856(1000.0, data);
    CHECK(tc_max31856_decode_x10(data) == 10000);

    /* Full K-type range: an int16_t of tenths must still hold it. */
    encode_31856(1372.0, data);
    CHECK(tc_max31856_decode_x10(data) == 13720);

    /* Negative values are the whole reason the sign extension exists.  Drop
       it and these come back as large positive temperatures - a reading that
       looks safe while the channel is broken. */
    encode_31856(-10.0, data);
    CHECK(tc_max31856_decode_x10(data) == -100);

    encode_31856(-200.0, data);
    CHECK(tc_max31856_decode_x10(data) == -2000);

    /* One LSB either side of zero. */
    encode_31856(0.125, data);
    CHECK(tc_max31856_decode_x10(data) == 1);
    encode_31856(-0.125, data);
    CHECK(tc_max31856_decode_x10(data) == -1);
}

static void test_max31856_fault_flags(void)
{
    CHECK(tc_max31856_fault_flags(0x00u) == HAL_TEMPERATURE_FAULT_NONE);
    CHECK((tc_max31856_fault_flags(0x01u) & HAL_TEMPERATURE_FAULT_OPEN) != 0u);
    CHECK((tc_max31856_fault_flags(0x02u) &
           HAL_TEMPERATURE_FAULT_VOLTAGE) != 0u);
    CHECK((tc_max31856_fault_flags(0x40u) &
           HAL_TEMPERATURE_FAULT_RANGE) != 0u);
    CHECK((tc_max31856_fault_flags(0x80u) &
           HAL_TEMPERATURE_FAULT_RANGE) != 0u);
    CHECK((tc_max31856_fault_flags(0x08u) &
           HAL_TEMPERATURE_FAULT_THRESHOLD) != 0u);
}

static void test_max6675_decode(void)
{
    CHECK(tc_max6675_decode_x10(0x0000u) == 0);
    /* 100.0 degC is 400 counts of 0.25 degC, left shifted by three. */
    CHECK(tc_max6675_decode_x10((uint16_t)(400u << 3)) == 1000);
    CHECK(tc_max6675_decode_x10((uint16_t)(1u << 3)) == 2);

    CHECK(!tc_max6675_frame_open((uint16_t)(400u << 3)));
    CHECK(tc_max6675_frame_open((uint16_t)((400u << 3) | 0x04u)));
    /* The open flag must not leak into the temperature. */
    CHECK(tc_max6675_decode_x10((uint16_t)((400u << 3) | 0x04u)) == 1000);
}

/* --- protection ------------------------------------------------------------ */

static void test_eight_channel_protection(void)
{
    app_protection_state_t protection;
    hal_temperature_sample_t samples[HAL_TEMPERATURE_BANK_CHANNELS];

    app_protection_reset(&protection);
    CHECK(app_protection_run_permitted(&protection));
    /* Nothing has been read yet, so nothing may run. */
    CHECK(!app_protection_output_permitted(false, &protection));
    CHECK(app_protection_output_permitted(true, &protection));

    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 1000);
    app_protection_evaluate(&protection, samples,
                            HAL_TEMPERATURE_BANK_CHANNELS, 1200);
    CHECK(!protection.latched);

    /* At the setpoint, not just above it. */
    samples[4].temperature_x10 = 1200;
    app_protection_evaluate(&protection, samples,
                            HAL_TEMPERATURE_BANK_CHANNELS, 1200);
    CHECK(protection.latched);
    CHECK(protection.cause == APP_TRIP_CAUSE_TEMPERATURE);
    CHECK(protection.first_channel == 4u);
    CHECK(!app_protection_output_permitted(true, &protection));

    /* Still hot: the latch must hold. */
    CHECK(!app_protection_try_ack(&protection, samples,
                                  HAL_TEMPERATURE_BANK_CHANNELS, 1150));
    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 1000);
    CHECK(app_protection_try_ack(&protection, samples,
                                 HAL_TEMPERATURE_BANK_CHANNELS, 1150));
    CHECK(!protection.latched);

    /* Any invalid sample is a trip, whatever the temperature says. */
    samples[2].valid = false;
    samples[2].faults = HAL_TEMPERATURE_FAULT_STUCK;
    app_protection_evaluate(&protection, samples,
                            HAL_TEMPERATURE_BANK_CHANNELS, 1200);
    CHECK(protection.latched);
    CHECK(protection.cause == APP_TRIP_CAUSE_SENSOR_FAULT);
    CHECK(protection.first_channel == 2u);
    /* And it cannot be acknowledged while the channel is still faulty. */
    CHECK(!app_protection_try_ack(&protection, samples,
                                  HAL_TEMPERATURE_BANK_CHANNELS, 1150));

    /* A missing sample array must fail safe, not be ignored. */
    app_protection_reset(&protection);
    app_protection_evaluate(&protection, NULL,
                            HAL_TEMPERATURE_BANK_CHANNELS, 1200);
    CHECK(protection.latched);
    app_protection_reset(&protection);
    app_protection_evaluate(&protection, samples, 0u, 1200);
    CHECK(protection.latched);
}

static void test_config_lock(void)
{
    app_protection_state_t protection;
    hal_temperature_sample_t samples[HAL_TEMPERATURE_BANK_CHANNELS];

    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 200);

    app_protection_reset(&protection);
    app_protection_config_lock(&protection);
    CHECK(protection.latched);
    CHECK(protection.config_locked);
    CHECK(protection.cause == APP_TRIP_CAUSE_CONFIG);
    CHECK(!app_protection_output_permitted(true, &protection));

    /* A blank unit must not be cleared into permitting the machine to run
       just because every channel happens to be cold. */
    CHECK(!app_protection_try_ack(&protection, samples,
                                  HAL_TEMPERATURE_BANK_CHANNELS, 1150));
    CHECK(protection.latched);

    app_protection_config_unlock(&protection);
    CHECK(app_protection_try_ack(&protection, samples,
                                 HAL_TEMPERATURE_BANK_CHANNELS, 1150));
    CHECK(!protection.latched);
}

static void test_drive_fault(void)
{
    app_protection_state_t protection;
    hal_temperature_sample_t samples[HAL_TEMPERATURE_BANK_CHANNELS];

    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 200);

    app_protection_reset(&protection);
    app_protection_note_drive_fault(&protection);
    CHECK(protection.latched);
    CHECK(protection.cause == APP_TRIP_CAUSE_DRIVE);

    /* The operator cannot acknowledge a driver that no longer works; the
       hardware has to be repaired. */
    CHECK(!app_protection_try_ack(&protection, samples,
                                  HAL_TEMPERATURE_BANK_CHANNELS, 1150));
    CHECK(protection.latched);
}

/* --- display --------------------------------------------------------------- */

static void test_channel_format(void)
{
    char text[17];
    hal_temperature_sample_t sample = good(1234);

    app_format_channel_line(text, 0u, &sample);
    CHECK(memcmp(text, "CH1:+ 123.4", 11) == 0);
    CHECK(memcmp(&text[14], "OK", 2) == 0);

    sample.valid = false;
    sample.faults = HAL_TEMPERATURE_FAULT_OPEN;
    app_format_channel_line(text, 2u, &sample);
    CHECK(memcmp(text, "CH3:---.-C ", 11) == 0);
    CHECK(memcmp(&text[11], "OPEN ", 5) == 0);

    /* The two plausibility faults must be distinguishable on the display,
       or a stuck sensor looks like any other fault. */
    sample.faults = HAL_TEMPERATURE_FAULT_STUCK;
    app_format_channel_line(text, 0u, &sample);
    CHECK(memcmp(&text[11], "STUCK", 5) == 0);

    sample.faults = HAL_TEMPERATURE_FAULT_RATE;
    app_format_channel_line(text, 0u, &sample);
    CHECK(memcmp(&text[11], "RATE ", 5) == 0);
}

static void test_status_line(void)
{
    app_protection_state_t protection;
    char text[17];

    app_protection_reset(&protection);
    app_format_status_line(text, &protection, 2000, false);
    CHECK(memcmp(text, "SP: 200", 7) == 0);
    CHECK(memcmp(&text[11], "SAFE", 4) == 0);
    CHECK(strlen(text) == 16u);

    app_format_status_line(text, &protection, 2000, true);
    CHECK(memcmp(text, "EDIT SP:", 8) == 0);

    protection.latched = true;
    protection.cause = APP_TRIP_CAUSE_TEMPERATURE;
    protection.first_channel = 2u;
    app_format_status_line(text, &protection, 2000, false);
    CHECK(memcmp(text, "TRIP CH3 TEMP", 13) == 0);

    protection.cause = APP_TRIP_CAUSE_DRIVE;
    app_format_status_line(text, &protection, 2000, false);
    CHECK(memcmp(text, "TRIP RELAY FAIL", 15) == 0);

    /* The config trip tells the operator what to do, not that it tripped. */
    app_protection_reset(&protection);
    app_protection_config_lock(&protection);
    app_format_status_line(text, &protection, 2000, false);
    CHECK(memcmp(text, "SET SETPOINT", 12) == 0);
}

/* --- sensor plausibility (I-011) ------------------------------------------ */

static void test_monitor_stuck(void)
{
    app_sensor_monitor_t monitor;
    hal_temperature_sample_t samples[HAL_TEMPERATURE_BANK_CHANNELS];
    uint16_t scan;

    app_sensor_monitor_reset(&monitor);

    /* The first scan primes the history and every scan after it holds the
       same value, so the counter runs out on the last one. */
    for (scan = 0u; scan <= APP_8CH_STUCK_SCANS; ++scan) {
        fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 800);
        app_sensor_monitor_update(&monitor, samples,
                                  HAL_TEMPERATURE_BANK_CHANNELS);
        if (scan < APP_8CH_STUCK_SCANS) {
            CHECK(samples[0].valid);
        }
    }
    CHECK(!samples[0].valid);
    CHECK((samples[0].faults & HAL_TEMPERATURE_FAULT_STUCK) != 0u);

    /* One tenth of a degree of movement is enough to clear it. */
    app_sensor_monitor_reset(&monitor);
    for (scan = 0u; scan <= APP_8CH_STUCK_SCANS; ++scan) {
        fill(samples, HAL_TEMPERATURE_BANK_CHANNELS,
             (int16_t)(800 + (scan & 1u)));
        app_sensor_monitor_update(&monitor, samples,
                                  HAL_TEMPERATURE_BANK_CHANNELS);
    }
    CHECK(samples[0].valid);
}

static void test_monitor_rate(void)
{
    app_sensor_monitor_t monitor;
    hal_temperature_sample_t samples[HAL_TEMPERATURE_BANK_CHANNELS];

    app_sensor_monitor_reset(&monitor);
    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 1000);
    app_sensor_monitor_update(&monitor, samples,
                              HAL_TEMPERATURE_BANK_CHANNELS);
    CHECK(samples[0].valid);

    /* Exactly at the limit is still physics. */
    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS,
         (int16_t)(1000 + APP_8CH_MAX_STEP_X10));
    app_sensor_monitor_update(&monitor, samples,
                              HAL_TEMPERATURE_BANK_CHANNELS);
    CHECK(samples[0].valid);

    /* One tenth beyond it is not. */
    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS,
         (int16_t)(1000 + 2 * APP_8CH_MAX_STEP_X10 + 1));
    app_sensor_monitor_update(&monitor, samples,
                              HAL_TEMPERATURE_BANK_CHANNELS);
    CHECK(!samples[0].valid);
    CHECK((samples[0].faults & HAL_TEMPERATURE_FAULT_RATE) != 0u);

    /* A drop is just as implausible as a rise. */
    app_sensor_monitor_reset(&monitor);
    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 1000);
    app_sensor_monitor_update(&monitor, samples,
                              HAL_TEMPERATURE_BANK_CHANNELS);
    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS,
         (int16_t)(1000 - APP_8CH_MAX_STEP_X10 - 1));
    app_sensor_monitor_update(&monitor, samples,
                              HAL_TEMPERATURE_BANK_CHANNELS);
    CHECK(!samples[0].valid);
}

static void test_monitor_ignores_invalid(void)
{
    app_sensor_monitor_t monitor;
    hal_temperature_sample_t samples[HAL_TEMPERATURE_BANK_CHANNELS];
    uint16_t scan;

    app_sensor_monitor_reset(&monitor);

    /* A channel the converter already rejected must not also collect a stuck
       fault, and must not be accused of one on its first reading back. */
    for (scan = 0u; scan <= APP_8CH_STUCK_SCANS; ++scan) {
        fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 800);
        samples[0].valid = false;
        samples[0].faults = HAL_TEMPERATURE_FAULT_OPEN;
        app_sensor_monitor_update(&monitor, samples,
                                  HAL_TEMPERATURE_BANK_CHANNELS);
    }
    CHECK(samples[0].faults == HAL_TEMPERATURE_FAULT_OPEN);

    fill(samples, HAL_TEMPERATURE_BANK_CHANNELS, 800);
    app_sensor_monitor_update(&monitor, samples,
                              HAL_TEMPERATURE_BANK_CHANNELS);
    CHECK(samples[0].valid);
}

/* --- stored setpoint (I-012) ---------------------------------------------- */

static void test_settings_round_trip(void)
{
    app_settings_t record;

    app_settings_build(&record, 1200);
    CHECK(record.magic == APP_SETTINGS_MAGIC);
    CHECK(record.setpoint_x10 == 1200);
    CHECK(app_settings_valid(&record));

    /* A single flipped bit anywhere in the record must not validate. */
    record.crc ^= 0x0001u;
    CHECK(!app_settings_valid(&record));

    app_settings_build(&record, 1200);
    record.setpoint_x10 = 1300;
    CHECK(!app_settings_valid(&record));

    app_settings_build(&record, 1200);
    record.magic ^= 0x0001u;
    CHECK(!app_settings_valid(&record));

    /* An erased EEPROM reads as all ones and must not look like a setpoint. */
    memset(&record, 0xFF, sizeof(record));
    CHECK(!app_settings_valid(&record));
    memset(&record, 0x00, sizeof(record));
    CHECK(!app_settings_valid(&record));

    /* A correct CRC over an out-of-range number is still not a setpoint. */
    app_settings_build(&record, (int16_t)(APP_8CH_MAX_SETPOINT_X10 + 10));
    CHECK(!app_settings_valid(&record));
    app_settings_build(&record, (int16_t)(APP_8CH_MIN_SETPOINT_X10 - 10));
    CHECK(!app_settings_valid(&record));

    /* Both ends of the allowed range are setpoints. */
    app_settings_build(&record, APP_8CH_MIN_SETPOINT_X10);
    CHECK(app_settings_valid(&record));
    app_settings_build(&record, APP_8CH_MAX_SETPOINT_X10);
    CHECK(app_settings_valid(&record));

    CHECK(!app_settings_valid(NULL));
}

int main(void)
{
    test_alarm_hysteresis();
    test_temperature_format();
    test_fault_text();
    test_max31856_decode();
    test_max31856_fault_flags();
    test_max6675_decode();
    test_eight_channel_protection();
    test_config_lock();
    test_drive_fault();
    test_channel_format();
    test_status_line();
    test_monitor_stuck();
    test_monitor_rate();
    test_monitor_ignores_invalid();
    test_settings_round_trip();

    if (failures != 0) {
        printf("%d check(s) failed\n", failures);
        return 1;
    }
    printf("all checks passed\n");
    return 0;
}
