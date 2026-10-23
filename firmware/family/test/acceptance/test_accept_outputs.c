#include "accept.h"
static void feedback_row(bool command, bool sense, bool alarm)
{
    outputs_t state; prot_out_t p; output_decision_t d;
    static const uint32_t times[]={0,59,60,160,161};
    unsigned i; char input[100];
    memset(&state,0,sizeof(state)); memset(&p,0,sizeof(p));
    /* 04 6.1 RUN window fixture; feedback assertions follow 04 6.2. */
    p.run_permission=alarm?true:command; p.window_remaining_ms=1200;
    p.alarm_active=alarm?!command:true;
    for(i=0;i<sizeof(times)/sizeof(times[0]);++i) {
        bool mismatch=command==sense;
        fault_code_t expected=mismatch&&times[i]>160 ?
            (alarm?FC_G07_ALARM_FEEDBACK:FC_G06_RUN_FEEDBACK):FC_NONE;
        d=outputs_step(&state,&p,times[i],alarm?true:sense,alarm?sense:true);
        (void)snprintf(input,sizeof(input),"%s command=%d sense_high=%d t=%lu",
                       alarm?"ALARM":"RUN",(int)command,(int)sense,(unsigned long)times[i]);
        EQ(P04 "6.2 active-low rows,60ms settle,>100ms filter",input,expected,alarm?d.alarm_fault:d.run_fault);
    }
}
void test_windows_outputs(void)
{
    rig_t r; unsigned i; outputs_t os; output_decision_t d; char input[100];
    rig_init(&r); rig_scan(&r,100); NO(P04 "6.1","validated scan START_LATCHED",r.out.run_permission);
    rig_ack(&r);
    EQ(P04 "6.1 ACK ordering","ACK uses preceding validated scan",RUN,r.state.mode);
    EQ(P04 "6.1 ACK ordering","ACK enters RUN with closed window",0,r.out.window_remaining_ms);
    memset(&os,0,sizeof(os)); d=outputs_step(&os,&r.out,100,true,true);
    NO(P04 "6.1 ACK ordering","ACK alone cannot start PWM",d.pwm_enable);
    NO(P04 "6.1 ACK ordering","ACK cannot refresh window",r.out.window_refresh);
    {
        rig_t same_scan;
        rig_init(&same_scan);same_scan.in.ack_key_released=true;rig_step(&same_scan);
        same_scan.in.ack_key_released=false;same_scan.in.ack=true;
        same_scan.in.ack_held_ms=50;same_scan.in.scan_complete=true;rig_step(&same_scan);
        EQ(P04 "6.1 ACK ordering / 8 scan-before-mailbox","ACK on same call as validated completion",RUN,same_scan.state.mode);
        EQ(P04 "6.1 ACK ordering","ACK+completion window remains closed",0,same_scan.out.window_remaining_ms);
        NO(P04 "6.1 ACK ordering","ACK+completion cannot refresh",same_scan.out.window_refresh);
        memset(&os,0,sizeof(os));d=outputs_step(&os,&same_scan.out,100,true,true);
        NO(P04 "6.1 ACK ordering","ACK+completion must wait for NEXT scan to start PWM",d.pwm_enable);
    }
    rig_scan(&r,101);
    YES(P04 "6.1","new validated scan in RUN opens window",r.out.run_permission);
    EQ(P04 "6.1","window length after new scan",1200,r.out.window_remaining_ms);
    r.in.now_ms=1300; rig_step(&r);
    YES(P04 "6.1","1199ms since refresh",r.out.run_permission);
    r.in.now_ms=1301; rig_step(&r);
    EQ(P04 "6.1 expiry / 09 S05/S26","1200ms since refresh",TRIPPED,r.state.mode);
    YES(P04 "6.1 expiry G05","1200ms since refresh",fault_active(&r.faults,FC_G05_SCAN_DEADLINE));
    NO(P04 "6.1 expiry","1200ms since refresh",r.out.run_permission);
    fault_clear(&r.faults,FC_G05_SCAN_DEADLINE,0); rig_scan(&r,1351);
    EQ(P04 "6.1 / 09 S25-S26","validated late scan at1250ms and fault cleared",TRIPPED,r.state.mode);
    NO(P04 "6.1 / 09 S26","late scan cannot reclose without ACK",r.out.run_permission);
    rig_ack(&r); EQ(P04 "6.1 ACK ordering","ACK after deadline trip",0,r.out.window_remaining_ms);
    rig_scan(&r,1352); YES(P04 "6.1","next scan after fresh ACK",r.out.run_permission);
    rig_init(&r); rig_ack(&r); r.in.now_ms=1300; rig_step(&r);
    EQ(P04 "6.1 ACK grace timeout","no new scan within1200ms of ACK",TRIPPED,r.state.mode);
    for(i=0;i<4;++i) {
        rig_running(&r); r.in.now_ms=500;
        r.in.scan_complete=i!=0;
        if(i==1) r.scan.scan_validated=false;
        if(i==2) r.scan.settings_seq=9;
        if(i==3) r.in.flow_ok=false;
        rig_step(&r);
        (void)snprintf(input,sizeof(input),"variant=%u no-completion/unvalidated/old-sequence/bad-flow",i);
        if(i!=3) NO(P04 "6.1 positive proof only",input,r.out.window_refresh);
        if(i==3) NO(P04 "6.1 flow check",input,r.out.run_permission);
        r.in.scan_complete=false; r.in.now_ms=1301; rig_step(&r);
        NO(P04 "6.1 no unauthorized extension",input,r.out.run_permission);
    }
    /* Expiry must be noticed BEFORE processing a scan that is already late. */
    rig_running(&r); rig_scan(&r,1351);
    EQ(P04 "6.1 late scan even without intervening loop","next call at1250ms with scan_complete",TRIPPED,r.state.mode);
    rig_init(&r); r.in.now_ms=UINT32_MAX-401u; r.scan.completed_ms=r.in.now_ms;
    rig_ack(&r); rig_scan(&r,UINT32_MAX-400u);
    r.in.now_ms=798; rig_step(&r);
    YES(P04 "6.1 / 00 uint32 time","window1199ms across ms_tick wrap",r.out.run_permission);
    r.in.now_ms=799; rig_step(&r);
    EQ(P04 "6.1 / 00 uint32 time","window1200ms across ms_tick wrap",TRIPPED,r.state.mode);
    rig_running(&r); r.scan.meas[0].temp_dC=1000;
    (void)prot_on_result(&r.state,0,&r.scan.meas[0],&r.cfg,r.scan.scan_no,0);
    rig_step(&r); NO(P04 "1","slot over-temp, scan_complete=false",r.out.run_permission);
    memset(&os,0,sizeof(os)); d=outputs_step(&os,&r.out,101,true,true);
    NO(P04 "1 outputs same loop","immediate trip stops PWM",d.pwm_enable);
    for(i=0;i<8;++i) feedback_row((i&1u)!=0,(i&2u)!=0,(i&4u)!=0);
    /* Recovering mismatch before100ms must reset its consecutive filter. */
    memset(&os,0,sizeof(os)); memset(&r.out,0,sizeof(r.out));
    r.out.run_permission=true; r.out.window_remaining_ms=1200; r.out.alarm_active=true;
    (void)outputs_step(&os,&r.out,0,true,true);
    (void)outputs_step(&os,&r.out,60,true,true);
    (void)outputs_step(&os,&r.out,159,false,true);
    (void)outputs_step(&os,&r.out,160,true,true);
    d=outputs_step(&os,&r.out,260,true,true);
    EQ(P04 "6.2 continuous mismatch","new mismatch exactly100ms",FC_NONE,d.run_fault);
    d=outputs_step(&os,&r.out,261,true,true);
    EQ(P04 "6.2 continuous mismatch","new mismatch101ms",FC_G06_RUN_FEEDBACK,d.run_fault);
    /* Simulated input crossing immediately after its prior slot. Actual core path
       is linked; scanner scheduling and mechanical delays are SPEC ASSUMPTIONS
       from 03 3.1/10.2 and 04 6.3 (690 ms normal, 1050 ms worst). */
    for(i=0;i<2;++i) {
        uint32_t cycle=i?1050u:690u, t, crossing=102, detection=crossing+cycle;
        uint32_t opened=0;
        rig_running(&r); memset(&os,0,sizeof(os));
        for(t=crossing;t<=detection+10u;++t) {
            r.in.now_ms=t;
            if(t==detection) {
                r.scan.meas[0].flags=tc_convert(CH_TYPE_K,4096000,0,&r.scan.meas[0].temp_dC);
                (void)prot_on_result(&r.state,0,&r.scan.meas[0],&r.cfg,r.scan.scan_no,t/1000u);
            }
            rig_step(&r); d=outputs_step(&os,&r.out,t,!r.out.run_permission,r.out.alarm_active);
            if(!d.pwm_enable&&opened==0) opened=t;
        }
        (void)snprintf(input,sizeof(input),"scan cycle=%lums",(unsigned long)cycle);
        EQ(P04 "1 and 6.3 immediate core path",input,detection,opened);
        YES("docs/GOAL.md Response time + 04 6.3",input,opened-crossing+5u+5u+30u+3u<=2000u);
        printf("TIMING | %s | crossing-to-core-off=%lu ms | conservative total=%lu ms (scan+5+5+30+3)\n",
               input,(unsigned long)(opened-crossing),(unsigned long)(cycle+43u));
    }
}
