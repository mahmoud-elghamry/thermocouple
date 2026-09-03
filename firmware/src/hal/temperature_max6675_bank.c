#include "hal/temperature_bank.h"
#include "mcal/board.h"
#include "mcal/gpio.h"
#include "mcal/spi.h"

#include <stddef.h>
#include <stdint.h>

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

    /* Proteus' MAX6675 model and the physical part use falling-edge data. */
    mcal_spi_master_init(MCAL_SPI_MODE_1);
    return true;
}

hal_temperature_sample_t hal_temperature_bank_read(uint8_t channel)
{
    hal_temperature_sample_t sample;
    uint16_t frame;
    uint16_t counts;
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

    frame = (uint16_t)((uint16_t)high << 8) | low;
    counts = (uint16_t)((frame & 0x7FF8u) >> 3);
    sample.temperature_x10 = (int16_t)(((uint32_t)counts * 10u) / 4u);
    sample.faults = ((frame & (uint16_t)(1u << 2)) != 0u)
                        ? HAL_TEMPERATURE_FAULT_OPEN
                        : HAL_TEMPERATURE_FAULT_NONE;
    sample.valid = sample.faults == HAL_TEMPERATURE_FAULT_NONE;
    return sample;
}
