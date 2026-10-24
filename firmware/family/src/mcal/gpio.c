#include "mcal/gpio.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
static volatile uint8_t *const ports[]={&PORTA,&PORTB,&PORTC,&PORTD};
static volatile uint8_t *const dirs[]={&DDRA,&DDRB,&DDRC,&DDRD};
void gpio_init(void) {
    uint8_t p;
    for(p=0;p<4;p++) *ports[p]=board()->port_init[p];
    for(p=0;p<4;p++) *dirs[p]=board()->ddr_init[p];
}
/* Every supported pin resolves to an atomic SBI/CBI. In particular, changing
 * another PB bit cannot undo Timer2's PB3 stop. No pin-table/variable shift. */
#define WRITE_CASE(P,b) case PIN(PORT_##P,b): if(h) PORT##P|=_BV(b); else PORT##P&=(uint8_t)~_BV(b); break;
void gpio_write(pin_t p,bool h) {
    switch(p) {
        WRITE_CASE(A,0) WRITE_CASE(A,1) WRITE_CASE(A,2) WRITE_CASE(A,3) WRITE_CASE(A,4) WRITE_CASE(A,5) WRITE_CASE(A,6) WRITE_CASE(A,7)
        WRITE_CASE(B,0) WRITE_CASE(B,1) WRITE_CASE(B,2) WRITE_CASE(B,3) WRITE_CASE(B,4) WRITE_CASE(B,5) WRITE_CASE(B,6) WRITE_CASE(B,7)
        WRITE_CASE(C,0) WRITE_CASE(C,1) WRITE_CASE(C,2) WRITE_CASE(C,3) WRITE_CASE(C,4) WRITE_CASE(C,5) WRITE_CASE(C,6) WRITE_CASE(C,7)
        WRITE_CASE(D,0) WRITE_CASE(D,1) WRITE_CASE(D,2) WRITE_CASE(D,3) WRITE_CASE(D,4) WRITE_CASE(D,5) WRITE_CASE(D,6) WRITE_CASE(D,7)
        default:break;
    }
}
#undef WRITE_CASE
#define READ_CASE(P,b) case PIN(PORT_##P,b): return (PIN##P&_BV(b))!=0;
bool gpio_read(pin_t p) {
    switch(p) {
        READ_CASE(A,0) READ_CASE(A,1) READ_CASE(A,2) READ_CASE(A,3) READ_CASE(A,4) READ_CASE(A,5) READ_CASE(A,6) READ_CASE(A,7)
        READ_CASE(B,0) READ_CASE(B,1) READ_CASE(B,2) READ_CASE(B,3) READ_CASE(B,4) READ_CASE(B,5) READ_CASE(B,6) READ_CASE(B,7)
        READ_CASE(C,0) READ_CASE(C,1) READ_CASE(C,2) READ_CASE(C,3) READ_CASE(C,4) READ_CASE(C,5) READ_CASE(C,6) READ_CASE(C,7)
        READ_CASE(D,0) READ_CASE(D,1) READ_CASE(D,2) READ_CASE(D,3) READ_CASE(D,4) READ_CASE(D,5) READ_CASE(D,6) READ_CASE(D,7)
        default:return false;
    }
}
#undef READ_CASE
void gpio_mask(uint8_t p,uint8_t m,uint8_t v) {
    if(p<4) *ports[p]=(uint8_t)((*ports[p]&(uint8_t)~m)|(v&m));
}
void delay_us(uint16_t us) {
    if(us==1) { _delay_us(1); return; }
    while(us--) _delay_us(1);
}
