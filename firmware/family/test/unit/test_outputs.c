#include "core_test.h"
void outputs_hw_apply(bool pwm, bool alarm, uint16_t remaining)
{ CHECK(!pwm || remaining>0); (void)alarm; }
void test_outputs(void)
{
    outputs_t s; prot_out_t p; output_decision_t d; unsigned cmd, sense;
    for(cmd=0;cmd<2;++cmd) for(sense=0;sense<2;++sense) {
        memset(&s,0,sizeof(s)); memset(&p,0,sizeof(p));
        p.run_permission=(cmd!=0); p.window_remaining_ms=APP_RUN_WINDOW_MS; p.alarm_active=(cmd==0);
        d=outputs_step(&s,&p,0,sense!=0,sense!=0);
        CHECK(d.run_fault==FC_NONE && d.alarm_fault==FC_NONE);
        d=outputs_step(&s,&p,59,sense!=0,sense!=0); CHECK(d.run_fault==FC_NONE);
        d=outputs_step(&s,&p,60,sense!=0,sense!=0); CHECK(d.run_fault==FC_NONE);
        d=outputs_step(&s,&p,160,sense!=0,sense!=0); CHECK(d.run_fault==FC_NONE);
        d=outputs_step(&s,&p,161,sense!=0,sense!=0);
        CHECK(d.run_fault==((cmd==sense)?FC_G06_RUN_FEEDBACK:FC_NONE));
        CHECK(d.alarm_fault==((cmd==sense)?FC_G07_ALARM_FEEDBACK:FC_NONE));
    }
    memset(&s,0,sizeof(s)); memset(&p,0,sizeof(p)); p.run_permission=true;
    d=outputs_step(&s,&p,0,true,true); CHECK(!d.pwm_enable); /* no window */
    p.window_remaining_ms=1; d=outputs_step(&s,&p,1,false,true); CHECK(d.pwm_enable);
    p.window_remaining_ms=0; d=outputs_step(&s,&p,2,true,true); CHECK(!d.pwm_enable);
    out_task(&d,0);
    p.window_remaining_ms=APP_RUN_WINDOW_MS+1u; d=outputs_step(&s,&p,3,true,true);
    CHECK(!d.pwm_enable && !d.alarm_energise && d.run_fault==FC_G04_INTERNAL);
}
