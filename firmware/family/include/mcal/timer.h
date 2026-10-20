#ifndef FAMILY_TIMER_H
#define FAMILY_TIMER_H
#include "common/types.h"
void timer_init(void);
uint32_t tick_ms(void);
void timer_tick_isr(void);
/* Atomic deadline, 0..1000 ms. ISR can only stop RUN. */
void timer_run_start(uint16_t deadline_ms);
void timer_run_stop(void);
uint16_t timer_run_remaining(void);
bool timer_run_active(void);
void timer_run_static_high(void);
#endif
