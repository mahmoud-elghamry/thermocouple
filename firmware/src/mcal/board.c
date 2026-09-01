#include "mcal/board.h"

#include <avr/io.h>

const mcal_gpio_port_t BOARD_LCD_PORT = {
    .port = &PORTA,
    .ddr = &DDRA,
};

const mcal_gpio_pin_t BOARD_LCD_RS = {
    .port = &PORTA,
    .ddr = &DDRA,
    .pin_register = &PINA,
    .bit = PA0,
};

const mcal_gpio_pin_t BOARD_LCD_ENABLE = {
    .port = &PORTA,
    .ddr = &DDRA,
    .pin_register = &PINA,
    .bit = PA1,
};

const mcal_gpio_pin_t BOARD_SENSOR_CS = {
    .port = &PORTB,
    .ddr = &DDRB,
    .pin_register = &PINB,
    .bit = PB4,
};

const mcal_gpio_pin_t BOARD_ALARM_OUTPUT = {
    .port = &PORTB,
    .ddr = &DDRB,
    .pin_register = &PINB,
    .bit = PB3,
};
