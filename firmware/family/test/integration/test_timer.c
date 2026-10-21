/* Compile the production ISR, not the integration clock's timer model. */
#include "mcal/timer.h"
#include <avr/io.h>
#include <stdio.h>
#include <stdlib.h>
uint8_t TCCR0A,TCCR0B,TIMSK0,TCCR1A,TCCR1B,TIMSK1;
uint8_t ASSR,TCCR2A,TCCR2B,OCR2A,TIMSK2,TCNT0,OCR0A,PORTB;
static unsigned checks,samples;
#define CHECK(x) do { ++checks; if(!(x)) { printf("Timer ISR FAIL %d: %s\n",__LINE__,#x); exit(1); } } while(0)
void keys_sample_isr(void) { ++samples; }
void TIMER2_COMPA_vect(void);
int main(void) {
    timer_init(); CHECK(!timer_run_expired()); timer_run_start(2);
    TIMER2_COMPA_vect(); CHECK(timer_run_active() && timer_run_remaining()==1);
    TIMER2_COMPA_vect(); CHECK(!timer_run_active() && timer_run_expired() && !TCCR0B && !(PORTB&8));
    timer_run_stop(); timer_run_start(900); CHECK(!timer_run_active() && timer_run_expired());
    timer_run_static_high(); CHECK(!(PORTB&8) && timer_run_expired());
    timer_run_ack_expiry(); CHECK(!timer_run_expired());
    CHECK(timer_run_start_at(10,0) && timer_run_remaining()==8);
    timer_run_ack_expiry(); CHECK(timer_run_active());
    timer_run_stop(); CHECK(!timer_run_start_at(2,0) && timer_run_expired());
    timer_run_ack_expiry(); CHECK(timer_run_start_at(10,0));
    CHECK(samples==2); printf("Timer ISR: %u checks PASS\n",checks); return 0;
}
