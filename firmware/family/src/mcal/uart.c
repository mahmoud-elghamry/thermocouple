#include "mcal/uart.h"
#include <avr/io.h>
#include <avr/interrupt.h>
static volatile uint8_t rx[64],tx[64],rh,rt,th,tt;
void uart_init(void) {
    rh=rt=th=tt=0; UBRR0H=0; UBRR0L=51; UCSR0A=0;
    UCSR0B=_BV(RXEN0)|_BV(TXEN0)|_BV(RXCIE0); UCSR0C=6;
}
bool uart_put(uint8_t b) {
    uint8_t n=(uint8_t)((th+1)&63); if(n==tt) return false;
    tx[th]=b; th=n; UCSR0A=_BV(TXC0); UCSR0B|=_BV(UDRIE0); return true;
}
bool uart_get(uint8_t *b) { if(rh==rt) return false; *b=rx[rt]; rt=(uint8_t)((rt+1)&63); return true; }
bool uart_tx_complete(void) { return th==tt && (UCSR0A&_BV(TXC0))!=0; }
void uart_rx_isr(uint8_t b) { uint8_t n=(uint8_t)((rh+1)&63); if(n!=rt) { rx[rh]=b; rh=n; } }
void uart_tx_isr(void) { if(th==tt) UCSR0B&=(uint8_t)~_BV(UDRIE0); else { UDR0=tx[tt]; tt=(uint8_t)((tt+1)&63); } }
ISR(USART0_RX_vect) { uint8_t s=UCSR0A,b=UDR0; if(!(s&(_BV(FE0)|_BV(DOR0)|_BV(UPE0)))) uart_rx_isr(b); }
ISR(USART0_UDRE_vect) { uart_tx_isr(); }
