#ifndef FAMILY_LCD_H
#define FAMILY_LCD_H
#include "common/types.h"
void lcd_init(void);
void lcd_frame(const char frame[80]);
void lcd_task(void); /* <=8 characters, cooperative init/reinit every 10 s */
#endif
