#include "mcal/uart.h"
#include "mcal/timer.h"
#include <avr/io.h>
extern volatile uint8_t cycle_kind,cycle_value;
extern volatile uint16_t cycle_errors;
void cycle_begin(void);
void cycle_end(void);
void USART0_RX_vect(void);
void USART0_UDRE_vect(void);
void USART0_TX_vect(void);
void uart_cycles(void) {
    uint8_t i; uart_sample_t s; static const uint8_t bytes[]={0,128,255};
    uart_configure_rtu(1);
    for(i=0;i<65;i++) {
        UCSR0A=i&1u?_BV(FE0):0; UDR0=i; TCNT1=(uint16_t)(i*600u);
        cycle_value=i; cycle_kind=36; cycle_begin(); USART0_RX_vect(); cycle_end();
    }
    if(!uart_rx_sample(&s) || !s.flags) ++cycle_errors;
    uart_rx_isr(8);
    cycle_kind=37; cycle_begin(); bool got=uart_rx_sample(&s); cycle_end();
    if(!got) ++cycle_errors;
    /* Cover both quantisation branches, full-ring loss, and the empty pop. */
    for(i=0;i<3;i++) {
        uint8_t j; uart_configure_rtu(1);
        TCNT1=(uint16_t)(tick_ms()*1000u+(i==0?(uint32_t)-1:349u));
        for(j=0;j<(i==2?65:1);j++) uart_rx_isr(j);
        cycle_value=i; cycle_kind=37; cycle_begin(); got=uart_rx_sample(&s); cycle_end();
        if(!got || (i==2 && !s.flags)) ++cycle_errors;
    }
    cycle_kind=37; cycle_begin(); got=uart_rx_sample(&s); cycle_end();
    if(got) ++cycle_errors;
    cycle_kind=38; cycle_begin(); (void)timer_now_us(); cycle_end();
    UCSR0A=0;
    cycle_kind=39; cycle_begin(); bool sent=uart_binary_start(bytes,sizeof bytes); cycle_end();
    if(!sent) ++cycle_errors;
    for(i=0;i<4;i++) { cycle_kind=40; cycle_value=i; cycle_begin(); USART0_UDRE_vect(); cycle_end(); }
    if(!uart_binary_busy() || !(PORTD&128u)) ++cycle_errors;
    cycle_kind=41; cycle_begin(); USART0_TX_vect(); cycle_end();
    if(uart_binary_busy() || (PORTD&128u)) ++cycle_errors;
}
