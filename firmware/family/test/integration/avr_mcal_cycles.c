/* Cycle calibration of the unmodified target MCAL in GNU's AVR simulator.
 * Hardware registers are RAM in this simulator; explicitly set input levels. */
#include "mcal/gpio.h"
#include "mcal/spi.h"
#include "mcal/timer.h"
#include "app/timing.h"
#include "drivers/keys.h"
#include <avr/io.h>
volatile uint8_t cycle_kind,cycle_value;
volatile uint16_t cycle_errors;
__attribute__((noinline)) void cycle_begin(void) { __asm__ volatile("nop"); }
__attribute__((noinline)) void cycle_end(void) { __asm__ volatile("nop"); }
__attribute__((noinline)) void cycle_done(void) { for(;;) __asm__ volatile("nop"); }
void TIMER2_COMPA_vect(void);
void store_cycles(void);
void uart_cycles(void);
int main(void) {
    uint16_t i; uint8_t j; gpio_init(); timer_init(); keys_init();
    PINA=PINB=PINC=PIND=255;
    for(i=0;i<256;i++) {
        PORTB=0x9F;
        cycle_value=(uint8_t)i; cycle_kind=9;
        cycle_begin(); uint8_t rx=spi_soft_xfer((uint8_t)i); cycle_end();
        if(rx!=255 || (PORTB&0x9Fu)!=0x9Fu) ++cycle_errors;
    }
    PINB=0; if(spi_soft_xfer(0)!=0) ++cycle_errors; PINB=255;
    cycle_kind=2; cycle_begin(); gpio_write(PIN(PORT_D,7),true); cycle_end();
    cycle_kind=3; cycle_begin(); (void)gpio_read(PIN(PORT_D,7)); cycle_end();
    cycle_kind=4; cycle_begin(); gpio_mask(PORT_A,255,255); cycle_end();
    cycle_kind=5; cycle_begin(); delay_us(49); cycle_end();
    cycle_kind=11; cycle_begin(); (void)tick_ms(); cycle_end();
    cycle_kind=13; cycle_begin(); (void)timer_run_start_at(APP_RUN_WINDOW_MS,tick_ms()); cycle_end();
    cycle_kind=15; cycle_begin(); (void)timer_run_remaining(); cycle_end();
    cycle_kind=16; cycle_begin(); (void)timer_run_active(); cycle_end();
    for(i=0;i<256;i++) {
        PIND=(uint8_t)i; cycle_value=(uint8_t)i;
        for(j=0;j<8;j++) { cycle_kind=32; cycle_begin(); TIMER2_COMPA_vect(); cycle_end(); }
        if(keys_held()!=(uint8_t)((!(i&4u)?1:0)|(!(i&8u)?2:0)|(!(i&16u)?4:0)|(!(i&64u)?8:0))) ++cycle_errors;
    }
    timer_run_ack_expiry(); timer_run_start(1);
    cycle_kind=32; cycle_begin(); TIMER2_COMPA_vect(); cycle_end();
    if(!timer_run_expired() || timer_run_active() || (PORTB&8u)) ++cycle_errors;
    if(timer_run_start_at(APP_RUN_WINDOW_MS,tick_ms())) ++cycle_errors;
    uart_cycles(); store_cycles(); cycle_done();
}
