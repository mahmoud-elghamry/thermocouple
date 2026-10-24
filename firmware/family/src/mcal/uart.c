#include "mcal/uart.h"
#include "mcal/timer.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
#ifndef UART_DE_PORT
#define UART_DE_PORT PORTD
#define UART_DE_BIT 7
#endif
static volatile uint8_t rx[64],flags[64],tx[64],rh,rt,th,tt;
static volatile uint32_t stamp[64],lost_at;
static volatile bool overflow,binary,rtu;
static const uint8_t *volatile borrowed;
static volatile uint16_t position,length;
static void reset(void) { rh=rt=th=tt=0; overflow=binary=false; borrowed=0; position=length=0; }
void uart_init(void) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        reset(); rtu=false; UBRR0H=0; UBRR0L=51; UCSR0A=0;
        UCSR0B=_BV(RXEN0)|_BV(TXEN0)|_BV(RXCIE0); UCSR0C=6;
    }
}
void uart_configure_rtu(uint8_t baud) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        uint8_t i;
        UCSR0B=0; reset(); rtu=true; UART_DE_PORT&=(uint8_t)(255u^_BV(UART_DE_BIT));
        for(i=0;i<3 && (UCSR0A&_BV(RXC0));i++) { volatile uint8_t discard=UDR0; (void)discard; }
        UBRR0H=0; UBRR0L=baud?25:51; UCSR0A=_BV(TXC0);
        UCSR0C=6|_BV(USBS0); UCSR0B=_BV(RXEN0)|_BV(TXEN0)|_BV(RXCIE0);
    }
}
bool uart_put(uint8_t b) {
    uint8_t n=(uint8_t)((th+1)&63); if(rtu || n==tt) return false;
    tx[th]=b; th=n; UCSR0A=_BV(TXC0); UCSR0B|=_BV(UDRIE0); return true;
}
bool uart_rx_sample(uart_sample_t *s) {
    bool got=false;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        if(overflow) { s->byte=0; s->at_us=lost_at; s->flags=1; overflow=false; got=true; }
        else if(rh!=rt) {
            uint8_t index=(uint8_t)(rt&63u);
            s->byte=rx[index]; s->at_us=stamp[index]; s->flags=flags[index]; rt=(uint8_t)((rt+1)&127); got=true;
        }
    }
    if(got && rtu) s->at_us=timer_expand_capture(s->at_us);
    return got;
}
bool uart_get(uint8_t *b) { uart_sample_t s; if(!uart_rx_sample(&s) || s.flags) return false; *b=s.byte; return true; }
bool uart_tx_complete(void) { return !binary && th==tt && (UCSR0A&_BV(TXC0))!=0; }
bool uart_binary_busy(void) { return binary; }
bool uart_binary_start(const uint8_t *bytes,uint16_t n) {
    bool ok=false;
    if(!bytes || !n || n>256) return false;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        if(rtu && !binary && rh==rt && !overflow && !(UCSR0A&_BV(RXC0))) {
            borrowed=bytes; position=0; length=n; binary=true;
            UART_DE_PORT|=_BV(UART_DE_BIT); UCSR0A=_BV(TXC0);
            UCSR0B=(uint8_t)((UCSR0B&~_BV(TXCIE0))|_BV(UDRIE0)); ok=true;
        }
    }
    return ok;
}
void uart_rx_error_isr(uint8_t b,uint8_t error) {
    uint8_t n; uint32_t at;
    if(binary) return; /* suppress local echo through the final stop bit */
    at=rtu?timer_capture_isr():0; n=(uint8_t)((rh+1)&127);
    if(((rh-rt)&127)==64) { rh=rt=0; overflow=true; lost_at=at; return; }
    rx[rh&63u]=b; flags[rh&63u]=error?1:0; stamp[rh&63u]=at; rh=n;
}
void uart_rx_isr(uint8_t b) { uart_rx_error_isr(b,0); }
void uart_tx_isr(void) {
    if(binary) {
        if(position<length) UDR0=borrowed[position++];
        else { UCSR0B&=(uint8_t)(255u^_BV(UDRIE0)); UCSR0B|=_BV(TXCIE0); }
    } else if(th==tt) UCSR0B&=(uint8_t)(255u^_BV(UDRIE0));
    else { UDR0=tx[tt]; tt=(uint8_t)((tt+1)&63); }
}
void uart_complete_isr(void) {
    UCSR0B&=(uint8_t)(255u^_BV(TXCIE0));
    if(binary) { UART_DE_PORT&=(uint8_t)(255u^_BV(UART_DE_BIT)); binary=false; borrowed=0; }
}
ISR(USART0_RX_vect) { uint8_t s=UCSR0A,b=UDR0; uart_rx_error_isr(b,(uint8_t)(s&(_BV(FE0)|_BV(DOR0)|_BV(UPE0)))); }
ISR(USART0_UDRE_vect) { uart_tx_isr(); }
ISR(USART0_TX_vect) { uart_complete_isr(); }
