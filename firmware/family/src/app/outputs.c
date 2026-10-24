#include "app/outputs.h"
#include "app/timing.h"
#include <stddef.h>
static bool mismatch(rb_state_t *s, bool command, bool sense_high, uint32_t now)
{
    if(!s->initialized || s->command!=command) {
        s->initialized=true; s->command=command; s->changed_ms=now; s->mismatch=false;
    }
    if((uint32_t)(now-s->changed_ms)<60u) return false;
    if(command!=sense_high) { s->mismatch=false; return false; }
    if(!s->mismatch) { s->mismatch=true; s->mismatch_ms=now; }
    return (uint32_t)(now-s->mismatch_ms)>100u;
}
output_decision_t outputs_step(outputs_t *s, const prot_out_t *p, uint32_t now_ms,
                               bool run_sense_high, bool alarm_sense_high)
{
    output_decision_t d={false,false,FC_NONE,FC_NONE};
    if(s==NULL || p==NULL) { d.run_fault=FC_G04_INTERNAL; return d; }
    if(p->window_remaining_ms>APP_RUN_WINDOW_MS) { d.run_fault=FC_G04_INTERNAL; return d; }
    d.pwm_enable=p->run_permission && p->window_remaining_ms>0;
    d.alarm_energise=p->run_permission && !p->alarm_active;
    if(mismatch(&s->run,d.pwm_enable,run_sense_high,now_ms)) d.run_fault=FC_G06_RUN_FEEDBACK;
    if(mismatch(&s->alarm,d.alarm_energise,alarm_sense_high,now_ms)) d.alarm_fault=FC_G07_ALARM_FEEDBACK;
    if(d.run_fault!=FC_NONE || d.alarm_fault!=FC_NONE) { d.pwm_enable=false; d.alarm_energise=false; }
    return d;
}
