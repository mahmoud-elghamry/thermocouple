#ifndef FAMILY_GPIO_H
#define FAMILY_GPIO_H
#include "board/board_cfg.h"
/* Init writes PORT before DDR. Mask writes preserve unrelated pins. */
void gpio_init(void);
void gpio_write(pin_t pin, bool high);
bool gpio_read(pin_t pin);
void gpio_mask(uint8_t port, uint8_t mask, uint8_t value);
void delay_us(uint16_t us);
#endif
