#ifndef FAMILY_OUTPUTS_H
#define FAMILY_OUTPUTS_H
#include "app/protection.h"
typedef struct { bool command, initialized, mismatch; uint32_t changed_ms, mismatch_ms; } rb_state_t;
typedef struct { rb_state_t run, alarm; } outputs_t;
typedef struct { bool pwm_enable, alarm_energise; fault_code_t run_fault, alarm_fault; } output_decision_t;
/* Pure decision + feedback filter: active-low senses, 60 ms settle, >100 ms mismatch. */
output_decision_t outputs_step(outputs_t *s, const prot_out_t *p, uint32_t now_ms,
                               bool run_sense_high, bool alarm_sense_high);
/* Thin shell, Lane A implements outputs_hw.h. */
void out_task(const output_decision_t *d, uint16_t window_ms);
#endif
