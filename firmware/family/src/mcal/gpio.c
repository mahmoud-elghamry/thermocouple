#include "mcal/gpio.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
static volatile uint8_t *const ports[]={&PORTA,&PORTB,&PORTC,&PORTD};
static volatile uint8_t *const inputs[]={&PINA,&PINB,&PINC,&PIND};
static volatile uint8_t *const dirs[]={&DDRA,&DDRB,&DDRC,&DDRD};
void gpio_init(void) {
    uint8_t p;
    for(p=0;p<4;p++) *ports[p]=board()->port_init[p];
    for(p=0;p<4;p++) *dirs[p]=board()->ddr_init[p];
}
void gpio_write(pin_t p,bool h) {
    if(p<32) { uint8_t m=(uint8_t)(1u<<(p&7));
        uint8_t saved=SREG; cli(); /* preserve the ISR's PB3 stop during a shared-port write */
        if(h) *ports[p>>3]|=m; else *ports[p>>3]&=(uint8_t)~m;
        SREG=saved;
    }
}
bool gpio_read(pin_t p) { return p<32 && (*inputs[p>>3]&(1u<<(p&7)))!=0; }
void gpio_mask(uint8_t p,uint8_t m,uint8_t v) {
    if(p<4) *ports[p]=(uint8_t)((*ports[p]&(uint8_t)~m)|(v&m));
}
void delay_us(uint16_t us) { uint16_t i; for(i=0;i<us;i++) _delay_us(1); }
