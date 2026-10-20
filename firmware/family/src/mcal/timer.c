#include "mcal/timer.h"
#include "mcal/gpio.h"
#include "drivers/keys.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
static volatile uint32_t ms;
static volatile uint16_t deadline;
void timer_init(void) {
    ms=0; deadline=0; TCCR0A=0; TCCR0B=0; TIMSK0=0;
    TCCR1A=0; TCCR1B=2; TIMSK1=0;
    ASSR=0; TCCR2A=2; TCCR2B=4; OCR2A=124; TIMSK2=2;
}
uint32_t tick_ms(void) { uint32_t v; ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v=ms; } return v; }
void timer_run_stop(void) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { TCCR0A=0; PORTB&=(uint8_t)~8u; TCCR0B=0; deadline=0; }
}
void timer_run_start(uint16_t d) {
    if(d==0 || d>1000) { timer_run_stop(); return; }
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        deadline=d; TCNT0=0; OCR0A=249; TCCR0A=0x42; TCCR0B=2;
    }
}
uint16_t timer_run_remaining(void) { uint16_t v; ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v=deadline; } return v; }
bool timer_run_active(void) { return timer_run_remaining()!=0 && TCCR0B!=0; }
void timer_run_static_high(void) { timer_run_stop(); PORTB|=8; ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { deadline=1000; } }
void timer_tick_isr(void) { ++ms; if(deadline && --deadline==0) timer_run_stop(); keys_sample_isr(); }
ISR(TIMER2_COMPA_vect) { timer_tick_isr(); }
