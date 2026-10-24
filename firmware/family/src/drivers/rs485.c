#include "drivers/rs485.h"
#include "mcal/uart.h"
#include "mcal/gpio.h"
#include <string.h>
static char buffer[124];
static uint8_t length,pos;
static bool sending;
void rs485_init(void) { length=pos=0; sending=false; gpio_write(board()->de,false); uart_init(); }
bool rs485_busy(void) { return length!=0 || sending; }
bool rs485_line(const char *s) {
    uint8_t i;
    if(rs485_busy()) return false;
    for(i=0;i<120 && s[i];i++) buffer[i]=s[i];
    if(i==120) return false;
    buffer[i++]='\r'; buffer[i++]='\n'; length=i; pos=0; return true;
}
void rs485_task(void) {
    if(length && !sending) { gpio_write(board()->de,true); delay_us(3); sending=true; }
    if(sending && pos<length) { if(uart_put((uint8_t)buffer[pos])) ++pos; return; }
    if(sending && uart_tx_complete()) { gpio_write(board()->de,false); sending=false; length=0; }
}
