#ifndef MCAL_BOARD_H
#define MCAL_BOARD_H

#include "mcal/gpio.h"

#include <stdint.h>

/* Physical ATmega32A wiring used by both firmware variants. */
extern const mcal_gpio_port_t BOARD_LCD_PORT;
extern const mcal_gpio_pin_t BOARD_LCD_RS;
extern const mcal_gpio_pin_t BOARD_LCD_ENABLE;
extern const mcal_gpio_pin_t BOARD_SENSOR_CS;
extern const mcal_gpio_pin_t BOARD_SENSOR_CS_PINS[8];
extern const mcal_gpio_pin_t BOARD_ALARM_OUTPUT;
extern const mcal_gpio_pin_t BOARD_BUTTON_NEXT;
extern const mcal_gpio_pin_t BOARD_BUTTON_UP;
extern const mcal_gpio_pin_t BOARD_BUTTON_DOWN;
extern const mcal_gpio_pin_t BOARD_BUTTON_SET;
extern const mcal_gpio_pin_t BOARD_BUTTON_ACK;

#define BOARD_LCD_DATA_MASK 0xF0u
#define BOARD_SENSOR_COUNT 8u

/* PB3 is ATmega32A DIP-40 physical pin 4. */
#define BOARD_ALARM_OUTPUT_PORT_NAME "PB3"
#define BOARD_ALARM_OUTPUT_DIP_PIN   4u

#endif
