#include "hal/temperature_sensor.h"
#include "mcal/board.h"
#include "mcal/gpio.h"
#include "mcal/spi.h"

#include <stdint.h>

static uint16_t max6675_read_frame(void)
{
    uint16_t frame;

    mcal_gpio_write(&BOARD_SENSOR_CS, false);
    frame = (uint16_t)mcal_spi_transfer(0x00u) << 8;
    frame |= mcal_spi_transfer(0x00u);
    mcal_gpio_write(&BOARD_SENSOR_CS, true);
    return frame;
}

void hal_temperature_sensor_init(void)
{
    mcal_gpio_write(&BOARD_SENSOR_CS, true);
    mcal_gpio_output(&BOARD_SENSOR_CS);
    /* MAX6675 data is sampled on SCK's falling edge. */
    mcal_spi_master_init(MCAL_SPI_MODE_1);
}

hal_temperature_sample_t hal_temperature_sensor_read(void)
{
    uint16_t frame = max6675_read_frame();
    uint16_t counts = (uint16_t)((frame & 0x7FF8u) >> 3);
    bool open = (frame & (uint16_t)(1u << 2)) != 0u;
    hal_temperature_sample_t sample = {
        .temperature_x10 = (int16_t)(((uint32_t)counts * 10u) / 4u),
        .fault = open,
        .status_text = open ? "FAULT: OPEN" : "Sensor: OK",
    };
    return sample;
}

const char *hal_temperature_sensor_name(void)
{
    return "MAX6675";
}
