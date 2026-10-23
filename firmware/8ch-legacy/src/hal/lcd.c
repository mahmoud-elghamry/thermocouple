#include "hal/lcd.h"
#include "mcal/board.h"
#include "mcal/gpio.h"

#include <util/delay.h>

static void lcd_pulse_enable(void)
{
    mcal_gpio_write(&BOARD_LCD_ENABLE, true);
    _delay_us(5);
    mcal_gpio_write(&BOARD_LCD_ENABLE, false);
    _delay_us(100);
}

static void lcd_write_nibble(uint8_t value)
{
    mcal_gpio_port_write_mask(&BOARD_LCD_PORT, BOARD_LCD_DATA_MASK, value);
    lcd_pulse_enable();
}

static void lcd_write(uint8_t value, bool data)
{
    mcal_gpio_write(&BOARD_LCD_RS, data);
    lcd_write_nibble(value);
    lcd_write_nibble((uint8_t)(value << 4));
}

static void lcd_command(uint8_t command)
{
    lcd_write(command, false);
    if (command == 0x01u || command == 0x02u) {
        _delay_ms(2);
    }
}

void hal_lcd_init(void)
{
    mcal_gpio_output(&BOARD_LCD_RS);
    mcal_gpio_output(&BOARD_LCD_ENABLE);
    mcal_gpio_port_output_mask(&BOARD_LCD_PORT, BOARD_LCD_DATA_MASK);
    mcal_gpio_write(&BOARD_LCD_RS, false);
    mcal_gpio_write(&BOARD_LCD_ENABLE, false);
    mcal_gpio_port_write_mask(&BOARD_LCD_PORT, BOARD_LCD_DATA_MASK, 0u);

    _delay_ms(50);
    lcd_write_nibble(0x30u);
    _delay_ms(5);
    lcd_write_nibble(0x30u);
    _delay_us(200);
    lcd_write_nibble(0x30u);
    _delay_us(200);
    lcd_write_nibble(0x20u);
    _delay_us(200);

    lcd_command(0x28u); /* 4-bit, 2 lines, 5x8 font. */
    lcd_command(0x08u);
    hal_lcd_clear();
    lcd_command(0x06u);
    lcd_command(0x0Cu);
}

void hal_lcd_clear(void)
{
    lcd_command(0x01u);
}

void hal_lcd_goto(uint8_t row, uint8_t column)
{
    uint8_t address = (row == 0u) ? column : (uint8_t)(0x40u + column);
    lcd_command((uint8_t)(0x80u | address));
}

void hal_lcd_putc(char character)
{
    lcd_write((uint8_t)character, true);
}

void hal_lcd_puts(const char *text)
{
    while (*text != '\0') {
        hal_lcd_putc(*text++);
    }
}

void hal_lcd_print_line(uint8_t row, const char *text)
{
    uint8_t count = 0u;
    hal_lcd_goto(row, 0u);
    while (*text != '\0' && count < 16u) {
        hal_lcd_putc(*text++);
        ++count;
    }
    while (count < 16u) {
        hal_lcd_putc(' ');
        ++count;
    }
}
