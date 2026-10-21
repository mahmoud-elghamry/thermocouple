#include "drivers/lcd.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include <string.h>
static char wanted[80],shown[80];
static uint8_t init_step,cursor;
static uint32_t due,last_init;
static const uint8_t row[4]={0,0x40,0x14,0x54};
static void nibble(uint8_t n,bool data) {
    gpio_mask(PORT_A,0xF3,(uint8_t)((n<<4)|(data?1:0)));
    gpio_mask(PORT_A,2,2); delay_us(1); gpio_mask(PORT_A,2,0); delay_us(1);
}
static void byte(uint8_t b,bool data) { nibble((uint8_t)(b>>4),data); nibble(b&15,data); delay_us(45); }
void lcd_init(void) {
    memset(wanted,' ',sizeof wanted); memset(shown,0,sizeof shown);
    cursor=0; init_step=0; due=tick_ms()+40; last_init=tick_ms();
}
void lcd_frame(const char frame[80]) { memcpy(wanted,frame,80); }
void lcd_task(void) {
    uint8_t i,n=0;
    if(tick_ms()-last_init>=10000) { init_step=0; due=tick_ms()+40; last_init=tick_ms(); memset(shown,0,80); }
    if((int32_t)(tick_ms()-due)<0) return;
    if(init_step<8) {
        switch(init_step++) {
        case 0:nibble(3,false);due=tick_ms()+5;break;
        case 1:nibble(3,false);due=tick_ms()+1;break;
        case 2:nibble(3,false);due=tick_ms()+1;break;
        case 3:nibble(2,false);due=tick_ms()+1;break;
        case 4:byte(0x28,false);break; case 5:byte(0x0C,false);break;
        case 6:byte(6,false);break; default:byte(1,false);due=tick_ms()+2;break;
        } return;
    }
    for(i=0;i<80 && n<8;i++) {
        uint8_t p=cursor; if(++cursor==80) cursor=0;
        if(wanted[p]!=shown[p]) {
            byte((uint8_t)(0x80|((p%20)+row[p/20])),false);
            byte((uint8_t)wanted[p],true); shown[p]=wanted[p]; ++n;
        }
    }
}
