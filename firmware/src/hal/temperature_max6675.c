#include "hal/temperature_sensor.h"
#include "mcal/board.h"
#include "mcal/gpio.h"
#include "mcal/spi.h"

#include <stdint.h>

static bool max6675_read_frame(uint16_t *frame)
{
    uint8_t high;
    uint8_t low;
    bool ok;

    mcal_gpio_write(&BOARD_SENSOR_CS, false);
    ok = mcal_spi_transfer(0x00u, &high);
    ok = ok && mcal_spi_transfer(0x00u, &low);
    mcal_gpio_write(&BOARD_SENSOR_CS, true);

    if (!ok) {
        return false;
    }
    *frame = (uint16_t)((uint16_t)high << 8) | low;
    return true;
}

bool hal_temperature_sensor_init(void)
{
    mcal_gpio_write(&BOARD_SENSOR_CS, true);
    mcal_gpio_output(&BOARD_SENSOR_CS);
    /* MAX6675 data is sampled on SCK's falling edge. */
    mcal_spi_master_init(MCAL_SPI_MODE_1);
    return true;
}

hal_temperature_sample_t hal_temperature_sensor_read(void)
{
    uint16_t frame;
    uint16_t counts;
    bool open;
    hal_temperature_sample_t sample;

    if (!max6675_read_frame(&frame)) {
        sample.temperature_x10 = 0;
        sample.faults = HAL_TEMPERATURE_FAULT_COMMUNICATION;
        sample.valid = false;
        return sample;
    }

    counts = (uint16_t)((frame & 0x7FF8u) >> 3);
    open = (frame & (uint16_t)(1u << 2)) != 0u;
    sample.temperature_x10 = (int16_t)(((uint32_t)counts * 10u) / 4u);
    sample.faults = open ? HAL_TEMPERATURE_FAULT_OPEN
                         : HAL_TEMPERATURE_FAULT_NONE;
    sample.valid = !open;
    return sample;
}

const char *hal_temperature_sensor_name(void)
{
    return "MAX6675";
}
