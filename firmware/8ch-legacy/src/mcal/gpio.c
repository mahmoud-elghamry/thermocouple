#include "mcal/gpio.h"

void mcal_gpio_output(const mcal_gpio_pin_t *pin)
{
    *pin->ddr |= (uint8_t)(1u << pin->bit);
}

void mcal_gpio_input(const mcal_gpio_pin_t *pin, bool pull_up)
{
    *pin->ddr &= (uint8_t)~(1u << pin->bit);
    mcal_gpio_write(pin, pull_up);
}

void mcal_gpio_write(const mcal_gpio_pin_t *pin, bool high)
{
    if (high) {
        *pin->port |= (uint8_t)(1u << pin->bit);
    } else {
        *pin->port &= (uint8_t)~(1u << pin->bit);
    }
}

bool mcal_gpio_read(const mcal_gpio_pin_t *pin)
{
    return (*pin->pin_register & (uint8_t)(1u << pin->bit)) != 0u;
}

void mcal_gpio_port_output_mask(const mcal_gpio_port_t *port, uint8_t mask)
{
    *port->ddr |= mask;
}

void mcal_gpio_port_write_mask(const mcal_gpio_port_t *port,
                               uint8_t mask,
                               uint8_t value)
{
    *port->port = (uint8_t)((*port->port & (uint8_t)~mask) | (value & mask));
}
