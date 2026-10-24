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

/* Eight independent chip-selects share PB6/MISO and PB7/SCK.  PB3 remains
   the protection relay output; PB4 also keeps AVR hardware SS as an output. */
const mcal_gpio_pin_t BOARD_SENSOR_CS_PINS[8] = {
    { .port = &PORTB, .ddr = &DDRB, .pin_register = &PINB, .bit = PB0 },
    { .port = &PORTB, .ddr = &DDRB, .pin_register = &PINB, .bit = PB1 },
    { .port = &PORTB, .ddr = &DDRB, .pin_register = &PINB, .bit = PB2 },
    { .port = &PORTB, .ddr = &DDRB, .pin_register = &PINB, .bit = PB4 },
    { .port = &PORTC, .ddr = &DDRC, .pin_register = &PINC, .bit = PC0 },
    { .port = &PORTC, .ddr = &DDRC, .pin_register = &PINC, .bit = PC1 },
    { .port = &PORTC, .ddr = &DDRC, .pin_register = &PINC, .bit = PC6 },
    { .port = &PORTC, .ddr = &DDRC, .pin_register = &PINC, .bit = PC7 },
};

const mcal_gpio_pin_t BOARD_ALARM_OUTPUT = {
    .port = &PORTB,
    .ddr = &DDRB,
    .pin_register = &PINB,
    .bit = PB3,
};

/* Same physical pin as BOARD_ALARM_OUTPUT, under the name the eight-channel
   board actually uses.  The two are never linked into the same image; see
   hal/run_permit.h for why the alarm name must not travel to this board. */
const mcal_gpio_pin_t BOARD_RUN_PERMIT = {
    .port = &PORTB,
    .ddr = &DDRB,
    .pin_register = &PINB,
    .bit = PB3,
};

/* Divider from the Q1 drain (RELAY_LOW, 0 V or +24 V) through R53/R54.
   PC2 is JTAG TCK until JTAGEN is unprogrammed - see firmware/fuses.md. */
const mcal_gpio_pin_t BOARD_RUN_PERMIT_SENSE = {
    .port = &PORTC,
    .ddr = &DDRC,
    .pin_register = &PINC,
    .bit = PC2,
};

const mcal_gpio_pin_t BOARD_BUTTON_NEXT = {
    .port = &PORTD, .ddr = &DDRD, .pin_register = &PIND, .bit = PD2,
};

const mcal_gpio_pin_t BOARD_BUTTON_UP = {
    .port = &PORTD, .ddr = &DDRD, .pin_register = &PIND, .bit = PD3,
};

const mcal_gpio_pin_t BOARD_BUTTON_DOWN = {
    .port = &PORTD, .ddr = &DDRD, .pin_register = &PIND, .bit = PD4,
};

const mcal_gpio_pin_t BOARD_BUTTON_SET = {
    .port = &PORTD, .ddr = &DDRD, .pin_register = &PIND, .bit = PD5,
};

const mcal_gpio_pin_t BOARD_BUTTON_ACK = {
    .port = &PORTD, .ddr = &DDRD, .pin_register = &PIND, .bit = PD6,
};
