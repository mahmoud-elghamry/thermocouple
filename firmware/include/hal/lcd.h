#ifndef HAL_LCD_H
#define HAL_LCD_H

#include <stdint.h>

void hal_lcd_init(void);
void hal_lcd_clear(void);
void hal_lcd_goto(uint8_t row, uint8_t column);
void hal_lcd_putc(char character);
void hal_lcd_puts(const char *text);
void hal_lcd_print_line(uint8_t row, const char *text);

#endif
