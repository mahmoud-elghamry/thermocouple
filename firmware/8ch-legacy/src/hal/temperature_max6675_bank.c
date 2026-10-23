/* Eight MAX6675 converters - Proteus simulation only.
 *
 * The physical board carries MAX31856 (see temperature_max31856_bank.c).
 * This backend exists because Proteus has no MAX31856 model, and for a while
 * it was the ONLY eight-channel backend, which left the real board with no
 * firmware at all (I-030).  It is a simulation aid, not a product target.
 */

#include "hal/temperature_bank.h"
#include "hal/tc_decode.h"
#include "mcal/board.h"
#include "mcal/gpio.h"
#include "mcal/spi.h"

#include <stddef.h>
#include <stdint.h>

/* Real MAX6675 silicon shifts data out on the falling edge of SCK and is
   sampled on the rising edge: SPI mode 0.  The Proteus model only works in
   mode 1, so the simulation target overrides this (I-018).  The default is
   the silicon, so nobody ships the simulation's timing by accident. */
#ifndef HAL_MAX6675_SPI_MODE
#define HAL_MAX6675_SPI_MODE MCAL_SPI_MODE_0
#endif

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

    /* Deselect every converter before any CS pin becomes an output. */
    for (channel = 0u; channel < HAL_TEMPERATURE_BANK_CHANNELS; ++channel) {
        mcal_gpio_write(&BOARD_SENSOR_CS_PINS[channel], true);
    }
    for (channel = 0u; channel < HAL_TEMPERATURE_BANK_CHANNELS; ++channel) {
        mcal_gpio_output(&BOARD_SENSOR_CS_PINS[channel]);
    }

    mcal_spi_master_init(HAL_MAX6675_SPI_MODE);
    return true;
}

hal_temperature_sample_t hal_temperature_bank_read(uint8_t channel)
{
    hal_temperature_sample_t sample;
    uint16_t frame;
    uint8_t high;
    uint8_t low;
    bool ok;

    if (channel >= HAL_TEMPERATURE_BANK_CHANNELS) {
        return invalid_sample(HAL_TEMPERATURE_FAULT_RANGE);
    }

    mcal_gpio_write(&BOARD_SENSOR_CS_PINS[channel], false);
    ok = mcal_spi_transfer(0x00u, &high);
    ok = ok && mcal_spi_transfer(0x00u, &low);
    mcal_gpio_write(&BOARD_SENSOR_CS_PINS[channel], true);

    if (!ok) {
        return invalid_sample(HAL_TEMPERATURE_FAULT_COMMUNICATION);
    }

    frame = (uint16_t)(((uint16_t)high << 8) | low);
    sample.temperature_x10 = tc_max6675_decode_x10(frame);
    sample.faults = tc_max6675_frame_open(frame)
                        ? HAL_TEMPERATURE_FAULT_OPEN
                        : HAL_TEMPERATURE_FAULT_NONE;
    sample.valid = sample.faults == HAL_TEMPERATURE_FAULT_NONE;
    return sample;
}

const char *hal_temperature_bank_name(void)
{
    return "MAX6675 (SIM)";
}
