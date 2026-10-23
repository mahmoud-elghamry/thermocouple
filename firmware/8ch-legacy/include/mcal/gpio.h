#ifndef MCAL_GPIO_H
#define MCAL_GPIO_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    volatile uint8_t *port;
    volatile uint8_t *ddr;
    volatile uint8_t *pin_register;
    uint8_t bit;
} mcal_gpio_pin_t;

typedef struct {
    volatile uint8_t *port;
    volatile uint8_t *ddr;
} mcal_gpio_port_t;

void mcal_gpio_output(const mcal_gpio_pin_t *pin);
void mcal_gpio_input(const mcal_gpio_pin_t *pin, bool pull_up);
void mcal_gpio_write(const mcal_gpio_pin_t *pin, bool high);
bool mcal_gpio_read(const mcal_gpio_pin_t *pin);
void mcal_gpio_port_output_mask(const mcal_gpio_port_t *port, uint8_t mask);
void mcal_gpio_port_write_mask(const mcal_gpio_port_t *port,
                               uint8_t mask,
                               uint8_t value);

#endif
