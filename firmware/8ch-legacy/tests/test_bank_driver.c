/* Host integration tests that run the real temperature_max31856_bank.c
 * against an eight-channel register model, instead of exercising the pure
 * decode/protection modules on values a test made up.
 *
 * The model answers every SPI transfer - it never times out - which is
 * exactly the situation I-038 is about: mcal_spi_transfer completing tells
 * the driver only that the master finished clocking, not that the bytes
 * came from a live converter.  A MISO line stuck at a fixed level is
 * modelled as every register read returning that fixed byte regardless of
 * which channel or address was selected.
 *
 * Source list: firmware/sources/host_test_driver.txt
 */

#include "hal/temperature_bank.h"
#include "mcal/board.h"
#include "mcal/spi.h"

#include <stdio.h>
#include <string.h>

static int failures;
#define CHECK(condition)                                                     \
    do {                                                                     \
        if (!(condition)) {                                                  \
            printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #condition);      \
            ++failures;                                                      \
        }                                                                    \
    } while (0)

/* --- eight-channel register model ----------------------------------------- */

#define CHANNELS 8u
#define REG_COUNT 128u
#define WRITE_BIT 0x80u
#define REG_LTCBH 0x0Cu

/* Real board pins carry no meaning to the model; only their identity (which
   array slot) matters, so the fields stay zeroed. */
const mcal_gpio_pin_t BOARD_SENSOR_CS_PINS[CHANNELS] = {
    {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0},
};

static uint8_t regs[CHANNELS][REG_COUNT];
static uint8_t reg_address[CHANNELS];
static bool address_phase[CHANNELS];
static int selected_channel = -1;
static bool miso_stuck;
static uint8_t miso_stuck_value;

static void reset_model(void)
{
    memset(regs, 0, sizeof(regs));
    memset(reg_address, 0, sizeof(reg_address));
    memset(address_phase, 0, sizeof(address_phase));
    selected_channel = -1;
    miso_stuck = false;
    miso_stuck_value = 0x00u;
}

static void set_channel_temperature(uint8_t channel, double celsius)
{
    long counts = (long)(celsius * 128.0);
    unsigned long reg = ((unsigned long)(counts & 0x7FFFFL) << 5) & 0xFFFFFFUL;

    regs[channel][0x0Cu] = (uint8_t)((reg >> 16) & 0xFFu);
    regs[channel][0x0Du] = (uint8_t)((reg >> 8) & 0xFFu);
    regs[channel][0x0Eu] = (uint8_t)(reg & 0xFFu);
}

void mcal_gpio_output(const mcal_gpio_pin_t *pin) { (void)pin; }

void mcal_gpio_write(const mcal_gpio_pin_t *pin, bool high)
{
    int index = (int)(pin - BOARD_SENSOR_CS_PINS);

    if (index < 0 || index >= (int)CHANNELS) {
        return;
    }
    if (!high) {
        selected_channel = index;
        address_phase[index] = true;
    } else if (selected_channel == index) {
        selected_channel = -1;
    }
}

void mcal_spi_master_init(mcal_spi_mode_t mode) { (void)mode; }

bool mcal_spi_transfer(uint8_t value, uint8_t *received)
{
    uint8_t channel;

    if (selected_channel < 0) {
        *received = 0xFFu;
        return true;
    }
    channel = (uint8_t)selected_channel;

    if (miso_stuck) {
        *received = miso_stuck_value;
        /* A stuck line still has to consume the byte, or the model's own
           address tracking desyncs once it recovers. */
        if (address_phase[channel]) {
            reg_address[channel] = value;
            address_phase[channel] = false;
        } else {
            ++reg_address[channel];
        }
        return true;
    }

    if (address_phase[channel]) {
        reg_address[channel] = value;
        address_phase[channel] = false;
        *received = 0u;
        return true;
    }
    if ((reg_address[channel] & WRITE_BIT) != 0u) {
        regs[channel][reg_address[channel] & 0x7Fu] = value;
    } else {
        *received = regs[channel][reg_address[channel] & 0x7Fu];
    }
    ++reg_address[channel];
    return true;
}

/* --- scenarios -------------------------------------------------------------- */

static void test_init_then_one_settling_scan(void)
{
    hal_temperature_sample_t sample;

    reset_model();
    CHECK(hal_temperature_bank_init());
    set_channel_temperature(0u, 25.0);

    /* The very next read is still the settling scan - it must not be
       trusted even though the registers are already correct (I-038). */
    sample = hal_temperature_bank_read(0u);
    CHECK(!sample.valid);

    sample = hal_temperature_bank_read(0u);
    CHECK(sample.valid);
    CHECK(sample.temperature_x10 == 250);
}

static void test_miso_stuck_low_detected_immediately(void)
{
    hal_temperature_sample_t sample;

    reset_model();
    CHECK(hal_temperature_bank_init());
    set_channel_temperature(3u, 20.0);
    (void)hal_temperature_bank_read(3u); /* settling */
    sample = hal_temperature_bank_read(3u);
    CHECK(sample.valid); /* healthy before the fault */

    miso_stuck = true;
    miso_stuck_value = 0x00u;

    /* Detected on the very first scan after the line sticks, not after the
       121-scan stuck-reading heuristic that I-038 found the old code relied
       on. */
    sample = hal_temperature_bank_read(3u);
    CHECK(!sample.valid);
    CHECK((sample.faults & HAL_TEMPERATURE_FAULT_INIT) != 0u);

    /* And it stays invalid: reconfiguration cannot succeed while the line is
       still stuck, so the channel is never accepted back on a lucky read. */
    sample = hal_temperature_bank_read(3u);
    CHECK(!sample.valid);
}

static void test_miso_stuck_high_detected_immediately(void)
{
    hal_temperature_sample_t sample;

    reset_model();
    CHECK(hal_temperature_bank_init());
    set_channel_temperature(5u, 20.0);
    (void)hal_temperature_bank_read(5u); /* settling */
    CHECK(hal_temperature_bank_read(5u).valid);

    miso_stuck = true;
    miso_stuck_value = 0xFFu;

    sample = hal_temperature_bank_read(5u);
    CHECK(!sample.valid);
    CHECK((sample.faults & HAL_TEMPERATURE_FAULT_INIT) != 0u);
}

static void test_configuration_drift_including_averaging(void)
{
    hal_temperature_sample_t sample;

    reset_model();
    CHECK(hal_temperature_bank_init());
    set_channel_temperature(1u, 40.0);
    (void)hal_temperature_bank_read(1u); /* settling */
    CHECK(hal_temperature_bank_read(1u).valid);

    /* Simulate a register that reset or glitched into 8-sample averaging
       (CR1 bits [6:4] = 011) while the thermocouple type field is still
       correct.  The old read-back mask (0x0F) would have missed this. */
    regs[1u][0x01u] = 0x33u;

    sample = hal_temperature_bank_read(1u);
    CHECK(!sample.valid);
    CHECK((sample.faults & HAL_TEMPERATURE_FAULT_INIT) != 0u);

    /* Recovery: the driver reconfigures the channel back to the correct
       averaging and type - reported as one invalid (settling) scan - then
       reads normally on the call after that. */
    sample = hal_temperature_bank_read(1u);
    CHECK(!sample.valid);
    sample = hal_temperature_bank_read(1u);
    CHECK(sample.valid);
    CHECK(sample.temperature_x10 == 400);
}

static void test_faulty_channel_does_not_block_others(void)
{
    hal_temperature_sample_t broken;
    hal_temperature_sample_t healthy;

    reset_model();
    CHECK(hal_temperature_bank_init());
    set_channel_temperature(2u, 60.0);
    set_channel_temperature(6u, 30.0);
    (void)hal_temperature_bank_read(2u); /* settling, channel 2 */
    (void)hal_temperature_bank_read(6u); /* settling, channel 6 */
    CHECK(hal_temperature_bank_read(2u).valid);
    CHECK(hal_temperature_bank_read(6u).valid);

    /* Only channel 2 loses its register configuration. */
    regs[2u][0x00u] = 0x00u;

    /* Two scans while channel 2 detects the fault and then reconfigures and
       settles - channel 6 is read every time in between and is never
       affected by channel 2's recovery. */
    broken = hal_temperature_bank_read(2u); /* configuration_ok fails */
    healthy = hal_temperature_bank_read(6u);
    CHECK(!broken.valid);
    CHECK(healthy.valid);
    CHECK(healthy.temperature_x10 == 300);

    broken = hal_temperature_bank_read(2u); /* reconfigured, settling scan */
    healthy = hal_temperature_bank_read(6u);
    CHECK(!broken.valid);
    CHECK(healthy.valid);
    CHECK(healthy.temperature_x10 == 300);

    /* Channel 2 is trusted again on the scan after it settles. */
    broken = hal_temperature_bank_read(2u);
    healthy = hal_temperature_bank_read(6u);
    CHECK(broken.valid);
    CHECK(broken.temperature_x10 == 600);
    CHECK(healthy.valid);
    CHECK(healthy.temperature_x10 == 300);
}

static void test_healthy_zero_celsius_not_rejected(void)
{
    hal_temperature_sample_t sample;

    reset_model();
    CHECK(hal_temperature_bank_init());
    set_channel_temperature(7u, 0.0);
    (void)hal_temperature_bank_read(7u); /* settling */

    sample = hal_temperature_bank_read(7u);
    CHECK(sample.valid);
    CHECK(sample.temperature_x10 == 0);
    CHECK(sample.faults == HAL_TEMPERATURE_FAULT_NONE);
}

int main(void)
{
    test_init_then_one_settling_scan();
    test_miso_stuck_low_detected_immediately();
    test_miso_stuck_high_detected_immediately();
    test_configuration_drift_including_averaging();
    test_faulty_channel_does_not_block_others();
    test_healthy_zero_celsius_not_rejected();

    if (failures != 0) {
        printf("%d check(s) failed\n", failures);
        return 1;
    }
    printf("all checks passed\n");
    return 0;
}
