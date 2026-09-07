#include "hal/temperature_sensor.h"
#include "hal/tc_decode.h"
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
#define CR0_OCFAULT_10MS 0x10u
#define CR0_FILTER_50HZ  0x01u
#define CR1_K_TYPE 0x03u

#define CR0_CONFIG_MASK 0xB1u
#define CR1_TYPE_MASK   0x0Fu
#define CR0_STOP_CONFIG (CR0_OCFAULT_10MS | CR0_FILTER_50HZ)
#define CR0_RUN_CONFIG  (CR0_CMODE | CR0_STOP_CONFIG)

static void max_select(void)
{
    mcal_gpio_write(&BOARD_SENSOR_CS, false);
}

static void max_deselect(void)
{
    mcal_gpio_write(&BOARD_SENSOR_CS, true);
}

static bool max_write_register(uint8_t address, uint8_t value)
{
    uint8_t received;
    bool ok;

    max_select();
    ok = mcal_spi_transfer((uint8_t)(address | WRITE_BIT), &received);
    ok = ok && mcal_spi_transfer(value, &received);
    max_deselect();
    return ok;
}

static bool max_read_register(uint8_t address, uint8_t *value)
{
    uint8_t received;
    bool ok;

    max_select();
    ok = mcal_spi_transfer(address, &received);
    ok = ok && mcal_spi_transfer(0x00u, value);
    max_deselect();
    return ok;
}

static bool max_read_sample_bytes(uint8_t data[4])
{
    uint8_t received;
    uint8_t index;
    bool ok;

    max_select();
    ok = mcal_spi_transfer(REG_LTCBH, &received);
    for (index = 0u; ok && index < 4u; ++index) {
        ok = mcal_spi_transfer(0x00u, &data[index]);
    }
    max_deselect();
    return ok;
}

bool hal_temperature_sensor_init(void)
{
    uint8_t cr0;
    uint8_t cr1;

    mcal_gpio_write(&BOARD_SENSOR_CS, true);
    mcal_gpio_output(&BOARD_SENSOR_CS);
    mcal_spi_master_init(MCAL_SPI_MODE_1);

    /* Configure the 50 Hz filter only while conversion is stopped.  The
       10 ms open-circuit test matches this board's low-resistance input
       network and runs automatically once every 16 conversions. */
    if (!max_write_register(REG_CR0, CR0_STOP_CONFIG) ||
        !max_write_register(REG_CR1, CR1_K_TYPE) ||
        !max_read_register(REG_CR0, &cr0) ||
        !max_read_register(REG_CR1, &cr1) ||
        (cr0 & CR0_CONFIG_MASK) != CR0_STOP_CONFIG ||
        (cr1 & CR1_TYPE_MASK) != CR1_K_TYPE ||
        !max_write_register(REG_CR0, CR0_RUN_CONFIG) ||
        !max_read_register(REG_CR0, &cr0) ||
        (cr0 & CR0_CONFIG_MASK) != CR0_RUN_CONFIG) {
        return false;
    }
    return true;
}

hal_temperature_sample_t hal_temperature_sensor_read(void)
{
    uint8_t data[4];
    hal_temperature_sample_t sample;

    if (!max_read_sample_bytes(data)) {
        sample.temperature_x10 = 0;
        sample.faults = HAL_TEMPERATURE_FAULT_COMMUNICATION;
        sample.valid = false;
        return sample;
    }

    sample.temperature_x10 = tc_max31856_decode_x10(data);
    sample.faults = tc_max31856_fault_flags(data[3]);
    sample.valid = sample.faults == HAL_TEMPERATURE_FAULT_NONE;
    return sample;
}

const char *hal_temperature_sensor_name(void)
{
    return "MAX31856";
}
