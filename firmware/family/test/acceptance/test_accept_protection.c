#include "accept.h"
static void set_mode(prot_state_t *s, prot_mode_t mode)
{
    /* Inject a valid stored state solely to exercise each specified transition. */
    s->mode=mode; s->mode_inv=(uint8_t)~(uint8_t)mode;
    s->permit=(uint8_t)(mode==RUN); s->permit_inv=(uint8_t)~s->permit;
}
void test_protection(void)
{
    rig_t r; unsigned m,k; char input[100];
    for(k=0;k<4;++k) {
        bool set_ok=(k&1u)!=0,cal_ok=(k&2u)!=0;
        rig_init(&r); prot_init(&r.state,set_ok,cal_ok,false);
        EQ(P04 "4 boot", "settings/calibration validity combinations",k==3?START_LATCHED:CONFIG_LOCK,r.state.mode);
        prot_init(&r.state,set_ok,cal_ok,true);
        EQ(P04 "4 boot SERVICE precedence","SET held even on blank board",SERVICE,r.state.mode);
    }
    for(m=0;m<5;++m) {
        rig_init(&r); set_mode(&r.state,(prot_mode_t)m); rig_step(&r);
        (void)snprintf(input,sizeof(input),"from=%u no event",m);
        EQ(P04 "4 forbidden spontaneous transitions",input,m,r.state.mode);
        rig_init(&r); set_mode(&r.state,(prot_mode_t)m); rig_ack(&r);
        (void)snprintf(input,sizeof(input),"from=%u fresh cool ACK",m);
        EQ(P04 "4 ACK transitions",input,m==START_LATCHED||m==TRIPPED?RUN:m,r.state.mode);
        rig_init(&r); set_mode(&r.state,(prot_mode_t)m); r.in.settings_valid=false; rig_step(&r);
        (void)snprintf(input,sizeof(input),"from=%u runtime invalid settings",m);
        EQ(P04 "4 any except SERVICE -> CONFIG_LOCK",input,m==SERVICE?SERVICE:CONFIG_LOCK,r.state.mode);
        rig_init(&r); set_mode(&r.state,(prot_mode_t)m); r.in.calibration_valid=false;rig_step(&r);
        (void)snprintf(input,sizeof(input),"from=%u runtime invalid calibration",m);
        EQ(P04 "9 G10 CONFIG_LOCK",input,m==SERVICE?SERVICE:CONFIG_LOCK,r.state.mode);
        rig_init(&r); set_mode(&r.state,(prot_mode_t)m);
        r.in.commit_begin=true; r.in.protection_change=true; r.in.writing=true; rig_step(&r);
        (void)snprintf(input,sizeof(input),"from=%u begin protection save",m);
        EQ(P04 "4 protection commit before write",input,
           m==RUN||m==START_LATCHED||m==TRIPPED?START_LATCHED:m,r.state.mode);
        NO(P04 "4",input,r.out.run_permission);
        rig_init(&r); set_mode(&r.state,(prot_mode_t)m);
        r.in.commit_begin=true; r.in.protection_change=false; rig_step(&r);
        (void)snprintf(input,sizeof(input),"from=%u names-only save",m);
        EQ(P04 "4 names only preserve state",input,m,r.state.mode);
        rig_init(&r); set_mode(&r.state,(prot_mode_t)m);
        r.scan.meas[0].temp_dC=1000;
        (void)prot_on_result(&r.state,0,&r.scan.meas[0],&r.cfg,r.scan.scan_no,1);
        (void)snprintf(input,sizeof(input),"from=%u immediate OVER_TRIP",m);
        EQ(P04 "4 trip transition and SERVICE only reset",input,m==RUN?TRIPPED:m,r.state.mode);
        rig_init(&r); set_mode(&r.state,(prot_mode_t)m);
        (void)prot_on_fault(&r.state,&r.faults,FC_G08_ENGREF_LOST,0,CH_MODE_TRIP,0,1);
        (void)snprintf(input,sizeof(input),"from=%u immediate G08",m);
        EQ(P04 "4 fault transition and SERVICE only reset",input,m==RUN?TRIPPED:m,r.state.mode);
    }
    rig_init(&r); set_mode(&r.state,CONFIG_LOCK); r.in.commit_done=true;
    r.in.protection_change=true; rig_step(&r);
    EQ(P04 "4 CONFIG_LOCK -> START_LATCHED","valid settings committed and cal valid",START_LATCHED,r.state.mode);
    rig_init(&r); set_mode(&r.state,CONFIG_LOCK); r.in.commit_done=true;
    r.in.calibration_valid=false; rig_step(&r);
    EQ(P04 "4 CONFIG_LOCK retained","valid settings but cal invalid",CONFIG_LOCK,r.state.mode);
    for(k=0;k<3;++k) {
        rig_running(&r);
        if(k==0) r.state.mode=(prot_mode_t)99;
        if(k==1) r.state.mode_inv^=1;
        if(k==2) r.state.permit_inv^=1;
        rig_step(&r);
        (void)snprintf(input,sizeof(input),"corruption=%u (state,complement,permission)",k);
        EQ(P04 "4 corrupt state / 01 6",input,TRIPPED,r.state.mode);
        YES(P04 "4 G04",input,fault_active(&r.faults,FC_G04_INTERNAL));
        NO(P04 "6.1",input,r.out.run_permission);
    }
    /* One refusal reason at a time, plus exact timing boundaries. */
    rig_init(&r); r.in.ack=true; r.in.ack_held_ms=100; rig_step(&r);
    EQ(P04 "5 R1","ACK held from boot, never released",ACK_R1_RELEASE,r.out.ack_reason);
    rig_ack(&r); EQ(P04 "5 R1","release then fresh 50ms press",RUN,r.state.mode);
    for(k=49;k<=50;++k) {
        rig_init(&r); r.in.ack_key_released=true; rig_step(&r);
        r.in.ack_key_released=false; r.in.ack=true; r.in.ack_held_ms=(uint16_t)k; rig_step(&r);
        (void)snprintf(input,sizeof(input),"ACK held=%ums",k);
        EQ(P04 "5 R1 >=50ms",input,k==50?ACK_NONE:ACK_R1_RELEASE,r.out.ack_reason);
    }
    for(k=500;k<=501;++k) {
        rig_init(&r); r.in.ack_key_released=true; rig_step(&r);
        r.in.ack_key_released=false; r.in.ack=true; r.in.ack_held_ms=50;
        r.in.ack_age_ms=(uint16_t)k; rig_step(&r);
        (void)snprintf(input,sizeof(input),"queued ACK age=%ums",k);
        EQ(P04 "5 R1 expires after 500ms",input,k==500?ACK_NONE:ACK_R1_RELEASE,r.out.ack_reason);
    }
    for(k=0;k<4;++k) {
        rig_init(&r);
        if(k==0) r.scan.scan_validated=false;
        if(k==1) r.in.now_ms=1300; /* exactly 1200 ms old */
        if(k==2) r.scan.settings_seq=9;
        if(k==3) r.in.now_ms=1299;
        rig_ack(&r);
        (void)snprintf(input,sizeof(input),"R2 variant=%u invalid/1200ms/old-sequence/1199ms",k);
        EQ(P04 "5 R2",input,k==3?ACK_NONE:ACK_R2_SCAN,r.out.ack_reason);
    }
    rig_init(&r); (void)fault_raise(&r.faults,FC_B01_ADC_ID,0); rig_ack(&r);
    EQ(P04 "5 R3","fresh ACK with B01 active",ACK_R3_FAULT,r.out.ack_reason);
    NO(P04 "5 R3","fault still present",r.out.run_permission);
    rig_init(&r); r.scan.meas[0].temp_dC=901; rig_ack(&r);
    EQ(P04 "5 R4","temp=90.1C trip=100 band=10",ACK_R4_CHANNEL,r.out.ack_reason);
    rig_init(&r); r.scan.meas[0].temp_dC=900; rig_ack(&r);
    EQ(P04 "5 R4","temp=90.0C equal reset threshold",ACK_NONE,r.out.ack_reason);
    rig_init(&r); r.scan.meas[0].flags=MEAS_VALID|MEAS_OPEN; rig_ack(&r);
    EQ(P04 "5 R4","fresh ACK with TRIP channel still OPEN",ACK_R4_CHANNEL,r.out.ack_reason);
    rig_init(&r); r.scan.meas[0].temp_dC=1000; rig_ack(&r);
    YES(P04 "4.1 first-out after refused startup ACK","startup channel hot",r.state.first.valid);
    EQ(P04 "4.1 first-out after refused startup ACK","startup over-trip cause",FC_C10_OVER_TRIP,r.state.first.code);
    rig_init(&r); r.cfg.ch[0].mode=CH_MODE_ALARM_ONLY; r.scan.meas[0].temp_dC=1100; rig_ack(&r);
    EQ(P04 "5 R4 / 3.3","ALARM_ONLY hot does not block ACK",RUN,r.state.mode);
    rig_init(&r); r.in.writing=true; rig_ack(&r);
    EQ(P04 "5 R5","fresh ACK during EEPROM save",ACK_R5_SETTINGS,r.out.ack_reason);
    rig_init(&r); r.in.readback_off_ok=false; rig_ack(&r);
    EQ(P04 "5 R6","fresh ACK with inconsistent off feedback",ACK_R6_RELAY,r.out.ack_reason);
    rig_running(&r); r.in.ack_key_released=true; rig_step(&r);
    r.in.ack_key_released=false;
    r.in.commit_begin=true; r.in.protection_change=true; r.in.writing=true; rig_step(&r);
    r.in.commit_begin=false; r.in.writing=false; r.in.ack_key_released=false;
    r.in.ack=true; r.in.ack_held_ms=60; r.in.ack_age_ms=100; rig_step(&r);
    EQ(P04 "5 R1 settings invalidates queued ACK","ACK queued before settings edit",ACK_R1_RELEASE,r.out.ack_reason);
    rig_running(&r); r.scan.meas[0].temp_dC=1000;
    (void)prot_on_result(&r.state,0,&r.scan.meas[0],&r.cfg,r.scan.scan_no,12);
    EQ(P04 "1 immediate slot trip","100C crossing before board scan completion",TRIPPED,r.state.mode);
    EQ(P04 "4.1 first-out","first cause channel1",1,r.state.first.channel);
    EQ(P04 "4.1 first-out","over-trip cause",FC_C10_OVER_TRIP,r.state.first.code);
    EQ(P04 "4.1 first-out","crossing temperature",1000,r.state.first.value_dC);
    EQ(P04 "4.1 first-out","trip threshold",1000,r.state.first.threshold_dC);
    (void)prot_on_fault(&r.state,&r.faults,FC_G08_ENGREF_LOST,0,CH_MODE_TRIP,0,13);
    EQ(P04 "4.1 first-out retained","later G08",FC_C10_OVER_TRIP,r.state.first.code);
    fault_clear(&r.faults,FC_G08_ENGREF_LOST,0);
    r.scan.meas[0].temp_dC=600; r.in.ack=true; r.in.ack_held_ms=100; rig_step(&r);
    EQ(P04 "5 R1 after trip","held/queued pretrip ACK without release",ACK_R1_RELEASE,r.out.ack_reason);
    rig_ack(&r); EQ(P04 "4.1 accepted ACK clears first-out","cool new ACK",false,r.state.first.valid);
    /* Alarm latch is distinct from instantaneous alarm condition. */
    rig_running(&r); r.scan.meas[0].temp_dC=800;
    (void)prot_on_result(&r.state,0,&r.scan.meas[0],&r.cfg,r.scan.scan_no,1); rig_step(&r);
    YES(P04 "7.2 / 9 C11","equal alarm setpoint",r.out.alarm_active);
    r.scan.meas[0].temp_dC=701; rig_ack(&r);
    YES(P04 "7.2","ACK one LSB above alarm reset band",r.out.alarm_active);
    r.scan.meas[0].temp_dC=700; rig_ack(&r);
    NO(P04 "7.2","ACK exactly alarm reset band",r.out.alarm_active);
}
