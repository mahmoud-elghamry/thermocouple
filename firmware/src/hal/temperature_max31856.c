#include "hal/temperature_sensor.h"
#include "mcal/board.h"
#include "mcal/gpio.h"
#include "mcal/spi.h"

#include <stdint.h>

#define REG_CR0    0x00u
#define REG_CR1    0x01u
#define REG_LTCBH  0x0Cu
#define REG_SR     0x0Fu

#define WRITE_BIT  0x80u
#define CR0_CMODE  0x80u
#define CR1_K_TYPE 0x03u

#define FAULT_OPEN     0x01u
#define FAULT_OVUV     0x02u
#define FAULT_TCLOW    0x04u
#define FAULT_TCHIGH   0x08u
#define FAULT_CJLOW    0x10u
#define FAULT_CJHIGH   0x20u
#define FAULT_TCRANGE  0x40u
#define FAULT_CJRANGE  0x80u

static void max_select(void)
{
    mcal_gpio_write(&BOARD_SENSOR_CS, false);
}

static void max_deselect(void)
{
    mcal_gpio_write(&BOARD_SENSOR_CS, true);
}

static void max_write_register(uint8_t address, uint8_t value)
{
    max_select();
    (void)mcal_spi_transfer((uint8_t)(address | WRITE_BIT));
    (void)mcal_spi_transfer(value);
    max_deselect();
}

static uint8_t max_read_register(uint8_t address)
{
    uint8_t value;
    max_select();
    (void)mcal_spi_transfer(address);
    value = mcal_spi_transfer(0x00u);
    max_deselect();
    return value;
}

static int16_t max_read_temperature_x10(void)
{
    int32_t raw;

    max_select();
    (void)mcal_spi_transfer(REG_LTCBH);
    raw = (int32_t)mcal_spi_transfer(0x00u) << 16;
    raw |= (int32_t)mcal_spi_transfer(0x00u) << 8;
    raw |= (int32_t)mcal_spi_transfer(0x00u);
    max_deselect();

    if ((raw & 0x00800000L) != 0) {
        raw |= (int32_t)0xFF000000L;
    }
    raw >>= 5;
    return (int16_t)((raw * 10L) / 128L);
}

static const char *fault_text(uint8_t fault)
{
    if ((fault & FAULT_OPEN) != 0u) {
        return "FAULT: OPEN";
    }
    if ((fault & FAULT_OVUV) != 0u) {
        return "FAULT: VOLTAGE";
    }
    if ((fault & (FAULT_TCRANGE | FAULT_CJRANGE)) != 0u) {
        return "FAULT: RANGE";
    }
    if ((fault & (FAULT_TCHIGH | FAULT_CJHIGH)) != 0u) {
        return "FAULT: HIGH";
    }
    if ((fault & (FAULT_TCLOW | FAULT_CJLOW)) != 0u) {
        return "FAULT: LOW";
    }
    return "Sensor: OK";
}

void hal_temperature_sensor_init(void)
{
    mcal_gpio_write(&BOARD_SENSOR_CS, true);
    mcal_gpio_output(&BOARD_SENSOR_CS);
    mcal_spi_master_init(MCAL_SPI_MODE_1);
    max_write_register(REG_CR1, CR1_K_TYPE);
    max_write_register(REG_CR0, CR0_CMODE);
}

hal_temperature_sample_t hal_temperature_sensor_read(void)
{
    uint8_t fault = max_read_register(REG_SR);
    hal_temperature_sample_t sample = {
        .temperature_x10 = max_read_temperature_x10(),
        .fault = fault != 0u,
        .status_text = fault_text(fault),
    };
    return sample;
}

const char *hal_temperature_sensor_name(void)
{
    return "MAX31856";
}
