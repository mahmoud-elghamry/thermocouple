#include "mcal/timer.h"
#include "mcal/gpio.h"
#include "drivers/keys.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
static volatile uint32_t ms;
static volatile uint16_t deadline;
static volatile bool expired;
void timer_init(void) {
    ms=0; deadline=0; expired=false; TCCR0A=0; TCCR0B=0; TIMSK0=0;
    TCCR1A=0; TCCR1B=2; TIMSK1=0;
    ASSR=0; TCCR2A=2; TCCR2B=4; OCR2A=124; TIMSK2=2;
}
uint32_t tick_ms(void) { uint32_t v; ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v=ms; } return v; }
void timer_run_stop(void) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { TCCR0A=0; PORTB&=0xF7u; TCCR0B=0; deadline=0; }
}
bool timer_run_start_at(uint16_t d,uint32_t evaluated) {
    bool started=false;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        uint32_t age=ms-evaluated;
        if(d && d<=1000 && age>=d) expired=true;
        if(!expired && d && d<=1000 && age<d) {
            deadline=(uint16_t)(d-age); TCNT0=0; OCR0A=249; TCCR0A=0x42; TCCR0B=2; started=true;
        } else timer_run_stop();
    }
    return started;
}
void timer_run_start(uint16_t d) { (void)timer_run_start_at(d,tick_ms()); }
bool timer_run_expired(void) { return expired; }
void timer_run_ack_expiry(void) { ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { if(!deadline && !TCCR0B) expired=false; } }
uint16_t timer_run_remaining(void) { uint16_t v; ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v=deadline; } return v; }
bool timer_run_active(void) { return timer_run_remaining()!=0 && TCCR0B!=0; }
void timer_run_static_high(void) { timer_run_stop(); ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { if(!expired) { PORTB|=8; deadline=1000; } } }
void timer_tick_isr(void) { ++ms; if(deadline && --deadline==0) { expired=true; timer_run_stop(); } keys_sample_isr(); }
ISR(TIMER2_COMPA_vect) { timer_tick_isr(); }
