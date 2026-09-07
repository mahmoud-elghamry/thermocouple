/* Eight MAX31856 converters on one SPI bus, one chip-select each.
 *
 * This is the driver for the eight-channel board (U2..U9).  It replaces the
 * MAX6675 bank, which only ever existed because Proteus has no MAX31856
 * model, and which left the real board with no firmware at all (I-030).
 *
 * Every channel carries its own configured/not-configured state.  A channel
 * that fails to answer is re-configured on the next scan instead of dragging
 * the whole bank down, and it reads as a fault while it is down, so the
 * protection layer latches rather than trusting a stale number.
 */

#include "hal/temperature_bank.h"
#include "hal/tc_decode.h"
#include "mcal/board.h"
#include "mcal/gpio.h"
#include "mcal/spi.h"

#include <stddef.h>
#include <stdint.h>

/* Register map. */
#define REG_CR0    0x00u
#define REG_CR1    0x01u
#define REG_MASK   0x02u
#define REG_LTCBH  0x0Cu
#define REG_SR     0x0Fu
#define WRITE_BIT  0x80u

/* CR0: automatic conversion, 10 ms open-circuit test, 50 Hz rejection.
   The open-circuit test needs the total input resistance below 5 kOhm; the
   100 R series resistors plus 50 m of extension wire stay well under it. */
#define CR0_CMODE        0x80u
#define CR0_OCFAULT_10MS 0x10u
#define CR0_FILTER_50HZ  0x01u
#define CR0_CONFIG_MASK  0xB1u
#define CR0_STOP_CONFIG  (CR0_OCFAULT_10MS | CR0_FILTER_50HZ)
#define CR0_RUN_CONFIG   (CR0_CMODE | CR0_STOP_CONFIG)

/* CR1: K type, no averaging.  Averaging would multiply the conversion time
   and eat into the 1 s trip budget for no accuracy this unit needs. */
#define CR1_K_TYPE      0x03u
#define CR1_TYPE_MASK   0x0Fu

/* Fault mask register: 0x00 unmasks every fault so the status register
   reports all of them.  FAULT and DRDY are unconnected on this board
   (docs/decisions/0004), so the status register is the only path. */
#define MASK_ALL_FAULTS 0x00u

static uint8_t configured;   /* one bit per channel */

static void select_channel(uint8_t channel)
{
    mcal_gpio_write(&BOARD_SENSOR_CS_PINS[channel], false);
}

static void deselect_channel(uint8_t channel)
{
    mcal_gpio_write(&BOARD_SENSOR_CS_PINS[channel], true);
}

static bool write_register(uint8_t channel, uint8_t address, uint8_t value)
{
    uint8_t received;
    bool ok;

    select_channel(channel);
    ok = mcal_spi_transfer((uint8_t)(address | WRITE_BIT), &received);
    ok = ok && mcal_spi_transfer(value, &received);
    deselect_channel(channel);
    return ok;
}

static bool read_register(uint8_t channel, uint8_t address, uint8_t *value)
{
    uint8_t received;
    bool ok;

    select_channel(channel);
    ok = mcal_spi_transfer(address, &received);
    ok = ok && mcal_spi_transfer(0x00u, value);
    deselect_channel(channel);
    return ok;
}

/* LTCBH, LTCBM, LTCBL and SR in one burst.  The MAX31856 auto-increments,
   and SR follows the temperature registers, so one transaction gives both
   the reading and the fault flags that qualify it. */
static bool read_sample_bytes(uint8_t channel, uint8_t data[4])
{
    uint8_t received;
    uint8_t index;
    bool ok;

    select_channel(channel);
    ok = mcal_spi_transfer(REG_LTCBH, &received);
    for (index = 0u; ok && index < 4u; ++index) {
        ok = mcal_spi_transfer(0x00u, &data[index]);
    }
    deselect_channel(channel);
    return ok;
}

/* Write the configuration while conversion is stopped, read it back, then
   start converting.  Reading it back is what turns a dead or mis-wired
   channel into a fault instead of a plausible number. */
static bool configure_channel(uint8_t channel)
{
    uint8_t cr0;
    uint8_t cr1;

    if (!write_register(channel, REG_CR0, CR0_STOP_CONFIG) ||
        !write_register(channel, REG_CR1, CR1_K_TYPE) ||
        !write_register(channel, REG_MASK, MASK_ALL_FAULTS) ||
        !read_register(channel, REG_CR0, &cr0) ||
        !read_register(channel, REG_CR1, &cr1) ||
        (cr0 & CR0_CONFIG_MASK) != CR0_STOP_CONFIG ||
        (cr1 & CR1_TYPE_MASK) != CR1_K_TYPE ||
        !write_register(channel, REG_CR0, CR0_RUN_CONFIG) ||
        !read_register(channel, REG_CR0, &cr0) ||
        (cr0 & CR0_CONFIG_MASK) != CR0_RUN_CONFIG) {
        return false;
    }
    return true;
}

static hal_temperature_sample_t invalid_sample(uint8_t faults)
{
    hal_temperature_sample_t sample;

    sample.temperature_x10 = 0;
    sample.faults = faults;
    sample.valid = false;
    return sample;
}

bool hal_temperature_bank_init(void)
{
    uint8_t channel;
    bool all_ok = true;

    /* Drive every chip-select high before any of them becomes an output, so
       no converter is selected while the bus is still undefined. */
    for (channel = 0u; channel < HAL_TEMPERATURE_BANK_CHANNELS; ++channel) {
        mcal_gpio_write(&BOARD_SENSOR_CS_PINS[channel], true);
    }
    for (channel = 0u; channel < HAL_TEMPERATURE_BANK_CHANNELS; ++channel) {
        mcal_gpio_output(&BOARD_SENSOR_CS_PINS[channel]);
    }

    /* MAX31856: data is latched on the falling edge and shifted out on the
       rising edge - SPI mode 1 (CPOL = 0, CPHA = 1). */
    mcal_spi_master_init(MCAL_SPI_MODE_1);

    configured = 0u;
    for (channel = 0u; channel < HAL_TEMPERATURE_BANK_CHANNELS; ++channel) {
        if (configure_channel(channel)) {
            configured |= (uint8_t)(1u << channel);
        } else {
            all_ok = false;
        }
    }
    return all_ok;
}

hal_temperature_sample_t hal_temperature_bank_read(uint8_t channel)
{
    hal_temperature_sample_t sample;
    uint8_t data[4];
    uint8_t mask;

    if (channel >= HAL_TEMPERATURE_BANK_CHANNELS) {
        return invalid_sample(HAL_TEMPERATURE_FAULT_RANGE);
    }
    mask = (uint8_t)(1u << channel);

    /* A channel that lost the bus is re-configured here rather than in a
       separate recovery path, so there is exactly one place that can bring
       a converter back (I-014). */
    if ((configured & mask) == 0u) {
        if (!configure_channel(channel)) {
            return invalid_sample(HAL_TEMPERATURE_FAULT_INIT);
        }
        configured |= mask;
    }

    if (!read_sample_bytes(channel, data)) {
        configured &= (uint8_t)~mask;
        return invalid_sample(HAL_TEMPERATURE_FAULT_COMMUNICATION);
    }

    sample.temperature_x10 = tc_max31856_decode_x10(data);
    sample.faults = tc_max31856_fault_flags(data[3]);
    sample.valid = sample.faults == HAL_TEMPERATURE_FAULT_NONE;
    return sample;
}

const char *hal_temperature_bank_name(void)
{
    return "MAX31856";
}
