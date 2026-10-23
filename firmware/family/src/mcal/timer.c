#include "mcal/timer.h"
#include "app/timing.h"
#include "mcal/gpio.h"
#include "drivers/keys.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
#ifdef __AVR__
#include "app/keys_sample_avr.h"
#endif
static volatile uint32_t ms;
static volatile uint16_t deadline;
static volatile bool expired;
void timer_init(void) {
    ms=0; deadline=0; expired=false; TCCR0A=0; TCCR0B=0; TIMSK0=0;
    TCCR1A=0; TCCR1B=0; TIMSK1=0; TCNT1=0;
    ASSR=0; TCCR2A=2; TCNT2=0; OCR2A=124; TCCR1B=2; TCCR2B=4; TIMSK2=2;
}
uint32_t tick_ms(void) { uint32_t v; ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v=ms; } return v; }
static uint32_t quantise(uint32_t base,uint16_t raw) {
    int16_t fine;
    base*=1000u;
    /* Tick ISR latency is harmless: Timer1 supplies the fraction (including a
     * pending tick). Calls are less than 65 ms apart while the loop is healthy. */
    fine=(int16_t)(raw-(uint16_t)base);
    /* The two prescalers can differ by a few microseconds at a tick edge.
     * Round a negative fraction down too, never a false +65.536 ms jump. */
    if(fine<0) return base-(uint32_t)(((uint16_t)(0u-(uint16_t)fine)+49u)/50u)*50u;
    return base+(uint32_t)((uint16_t)fine/50u)*50u;
}
uint32_t timer_now_us(void) {
    uint32_t base; uint16_t raw;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { base=ms; raw=TCNT1; }
    return quantise(base,raw);
}
uint32_t timer_capture_isr(void) { return ((uint32_t)(uint16_t)ms<<16)|TCNT1; }
uint32_t timer_expand_capture(uint32_t capture) {
    uint32_t now=tick_ms(); uint16_t low=(uint16_t)(capture>>16);
    return quantise(now-(uint16_t)((uint16_t)now-low),(uint16_t)capture);
}
void timer_run_stop(void) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { TCCR0A=0; PORTB&=0xF7u; TCCR0B=0; deadline=0; }
}
bool timer_run_start_at(uint16_t d,uint32_t evaluated) {
    bool started=false;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        uint32_t age=ms-evaluated;
        if(d && d<=APP_RUN_WINDOW_MS && age>=d) expired=true;
        if(!expired && d && d<=APP_RUN_WINDOW_MS && age<d) {
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
void timer_run_static_high(void) { timer_run_stop(); ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { if(!expired) { PORTB|=8; deadline=APP_SERVICE_RELAY_MS; } } }
static inline void tick_isr_core(void) {
    ++ms;
    if(deadline && --deadline==0) {
        expired=true; TCCR0A=0; PORTB&=0xF7u; TCCR0B=0;
    }
}
void timer_tick_isr(void) { tick_isr_core(); keys_sample_isr(); }
ISR(TIMER2_COMPA_vect) {
    tick_isr_core();
#ifdef __AVR__
    keys_sample_fast();
#else
    keys_sample_isr();
#endif
}
