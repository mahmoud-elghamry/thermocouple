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
extern const mcal_gpio_pin_t BOARD_RUN_PERMIT;
extern const mcal_gpio_pin_t BOARD_RUN_PERMIT_SENSE;
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

/* Run-permit driver read-back (I-016).
 *
 * REV A0 does NOT have it: PC2 is an unconnected SPARE pin, so the check is
 * compiled out and hal_run_permit_readback_agrees() always reports agreement.
 * The R53/R54 divider from RELAY_LOW is part of the REV A1 change set in
 * docs/decisions/0010; set this to 1 in the same commit that adds it.
 *
 * PC2 is ATmega32A DIP-40 physical pin 24, and JTAG TCK until JTAGEN is
 * unprogrammed.  Without that fuse the read-back is meaningless even on A1. */
#ifndef BOARD_HAS_RUN_PERMIT_SENSE
#define BOARD_HAS_RUN_PERMIT_SENSE 0
#endif
#define BOARD_RUN_PERMIT_SENSE_PORT_NAME "PC2"
#define BOARD_RUN_PERMIT_SENSE_DIP_PIN   24u

#endif
