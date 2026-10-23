/* Compile the production ISR, not the integration clock's timer model. */
#include "mcal/timer.h"
#include "app/timing.h"
#include <avr/io.h>
#include <stdio.h>
#include <stdlib.h>
uint8_t TCCR0A,TCCR0B,TIMSK0,TCCR1A,TCCR1B,TIMSK1;
uint8_t ASSR,TCCR2A,TCCR2B,OCR2A,TIMSK2,TCNT0,OCR0A,PORTB;
uint8_t TCNT2;
uint16_t TCNT1;
static unsigned checks,samples;
#define CHECK(x) do { ++checks; if(!(x)) { printf("Timer ISR FAIL %d: %s\n",__LINE__,#x); exit(1); } } while(0)
void keys_sample_isr(void) { ++samples; }
void TIMER2_COMPA_vect(void);
int main(void) {
    timer_init(); CHECK(!timer_run_expired()); timer_run_start(2);
    TIMER2_COMPA_vect(); CHECK(timer_run_active() && timer_run_remaining()==1);
    TIMER2_COMPA_vect(); CHECK(!timer_run_active() && timer_run_expired() && !TCCR0B && !(PORTB&8));
    timer_run_stop(); timer_run_start(APP_RUN_WINDOW_MS); CHECK(!timer_run_active() && timer_run_expired());
    timer_run_static_high(); CHECK(!(PORTB&8) && timer_run_expired());
    timer_run_ack_expiry(); CHECK(!timer_run_expired());
    CHECK(timer_run_start_at(10,0) && timer_run_remaining()==8);
    timer_run_ack_expiry(); CHECK(timer_run_active());
    timer_run_stop(); CHECK(!timer_run_start_at(2,0) && timer_run_expired());
    timer_run_ack_expiry(); CHECK(timer_run_start_at(10,0));
    timer_init(); CHECK(timer_run_start_at(APP_RUN_WINDOW_MS,tick_ms()));
    { unsigned i; for(i=0;i<APP_RUN_WINDOW_MS-1u;i++) TIMER2_COMPA_vect(); }
    CHECK(timer_run_active() && timer_run_remaining()==1);
    TIMER2_COMPA_vect(); CHECK(timer_run_expired() && !timer_run_active());
    timer_run_ack_expiry(); CHECK(!timer_run_start_at(APP_RUN_WINDOW_MS+1u,tick_ms()));
    timer_run_static_high(); CHECK(timer_run_remaining()==APP_SERVICE_RELAY_MS);
    CHECK(samples==2+APP_RUN_WINDOW_MS);
    timer_init();
    { unsigned i; for(i=0;i<65;i++) timer_tick_isr(); }
    TCNT1=64999; CHECK(timer_now_us()==64950); /* prescaler phase at tick edge */
    TCNT1=65500; CHECK(timer_now_us()==65500);
    TCNT1=14; CHECK(timer_now_us()==65550); /* raw Timer1 wrap, tick still pending */
    timer_tick_isr(); TCNT1=514; CHECK(timer_now_us()==66050);
    { uint32_t captured=timer_capture_isr(); timer_tick_isr(); TCNT1=1514;
      CHECK(timer_expand_capture(captured)==66050 && timer_now_us()==67050); }
    timer_init();
    { unsigned i; uint32_t captured;
      for(i=0;i<65535;i++) timer_tick_isr();
      TCNT1=(uint16_t)(65535250UL&65535UL); captured=timer_capture_isr();
      timer_tick_isr(); timer_tick_isr(); TCNT1=(uint16_t)(65537250UL&65535UL);
      CHECK(timer_expand_capture(captured)==65535250UL && timer_now_us()==65537250UL); }
    printf("Timer ISR: %u checks PASS\n",checks); return 0;
}
