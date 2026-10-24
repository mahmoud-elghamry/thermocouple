#include "mcal/uart.h"
#include <avr/io.h>
#include <stdio.h>
#include <stdlib.h>
uint8_t UBRR0H,UBRR0L,UCSR0A,UCSR0B,UCSR0C,UDR0,PORTD;
static uint32_t now;
static unsigned checks;
uint32_t timer_now_us(void) { return now; }
uint32_t timer_capture_isr(void) { return now; }
uint32_t timer_expand_capture(uint32_t at) { return at; }
#define CHECK(x) do { ++checks; if(!(x)) { printf("UART FAIL %u: %s\n",__LINE__,#x); exit(1); } } while(0)
void USART0_RX_vect(void);
void USART0_TX_vect(void);
int main(void) {
    uart_sample_t s; unsigned i; const uint8_t tx[]={0,128,255};
    uart_init(); CHECK(!(UCSR0C&_BV(USBS0)));
    uart_configure_rtu(0); CHECK(UBRR0L==51 && (UCSR0C&_BV(USBS0)));
    uart_configure_rtu(1); CHECK(UBRR0L==25 && (UCSR0C&_BV(USBS0)));
    for(i=0;i<64;i++) { now=i*600u; uart_rx_isr((uint8_t)i); }
    for(i=0;i<64;i++) { CHECK(uart_rx_sample(&s) && !s.flags && s.byte==i && s.at_us==i*600u); }
    CHECK(!uart_rx_sample(&s));
    for(i=0;i<65;i++) { now=i*600u; uart_rx_isr((uint8_t)i); }
    CHECK(uart_rx_sample(&s) && s.flags && s.at_us==64u*600u);
    CHECK(!uart_rx_sample(&s)); /* overflow invalidates queued fragments */
    for(i=0;i<3;i++) {
        UCSR0A=(uint8_t)(i==0?_BV(FE0):i==1?_BV(DOR0):_BV(UPE0)); UDR0=(uint8_t)i;
        USART0_RX_vect(); CHECK(uart_rx_sample(&s) && s.flags && s.byte==i);
    }
    UCSR0A=_BV(RXC0); CHECK(!uart_binary_start(tx,sizeof tx)); UCSR0A=0;
    uart_rx_isr(3); CHECK(!uart_binary_start(tx,sizeof tx)); CHECK(uart_rx_sample(&s));
    CHECK(uart_binary_start(tx,sizeof tx) && uart_binary_busy() && (PORTD&128));
    for(i=0;i<3;i++) { uart_tx_isr(); CHECK(UDR0==tx[i] && uart_binary_busy() && (PORTD&128)); }
    uart_tx_isr(); CHECK(!(UCSR0B&_BV(UDRIE0)) && (UCSR0B&_BV(TXCIE0)) && uart_binary_busy());
    uart_rx_isr(99); CHECK(!uart_rx_sample(&s)); /* suppress echo */
    USART0_TX_vect(); CHECK(!uart_binary_busy() && !(PORTD&128));
    uart_rx_isr(7); uart_configure_rtu(0); CHECK(!uart_rx_sample(&s));
    printf("UART RTU: %u checks PASS\n",checks); return 0;
}
