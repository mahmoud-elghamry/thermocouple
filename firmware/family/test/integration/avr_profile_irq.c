/* Actual Timer2 ISR, injected at MCAL handoffs for integrated stack paint. */
#define timer_init profile_irq_timer_init
#define tick_ms profile_irq_tick_ms
#define timer_now_us profile_irq_timer_now_us
#define timer_capture_isr profile_irq_timer_capture_isr
#define timer_expand_capture profile_irq_timer_expand_capture
#define timer_tick_isr profile_irq_timer_tick_isr
#define timer_run_start profile_irq_timer_run_start
#define timer_run_start_at profile_irq_timer_run_start_at
#define timer_run_expired profile_irq_timer_run_expired
#define timer_run_ack_expiry profile_irq_timer_run_ack_expiry
#define timer_run_stop profile_irq_timer_run_stop
#define timer_run_remaining profile_irq_timer_run_remaining
#define timer_run_active profile_irq_timer_run_active
#define timer_run_static_high profile_irq_timer_run_static_high
#define uart_init profile_irq_uart_init
#define uart_configure_rtu profile_irq_uart_configure_rtu
#define uart_put profile_irq_uart_put
#define uart_rx_sample profile_irq_uart_rx_sample
#define uart_get profile_irq_uart_get
#define uart_tx_complete profile_irq_uart_tx_complete
#define uart_binary_busy profile_irq_uart_binary_busy
#define uart_binary_start profile_irq_uart_binary_start
#define uart_rx_error_isr profile_irq_uart_rx_error_isr
#define uart_rx_isr profile_irq_uart_rx_isr
#define uart_tx_isr profile_irq_uart_tx_isr
#define uart_complete_isr profile_irq_uart_complete_isr
#define keys_history profile_irq_history
#define keys_stable profile_irq_stable
#include "../../src/mcal/timer.c"
#include "../../src/mcal/uart.c"
volatile uint8_t profile_irq_history[5],profile_irq_stable;
void profile_interrupt(uint8_t pins) {
    static bool initialized;
    if(!initialized) { profile_irq_uart_configure_rtu(1); initialized=true; }
    PIND=pins;
    TIMER2_COMPA_vect();
    UCSR0A=0; UDR0=pins; USART0_RX_vect();
}
