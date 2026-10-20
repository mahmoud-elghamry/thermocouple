/* Boundary scenarios use real Lane B modules and scan_out_t sequences. They do
 * not claim to exercise Lane A's ADC retries, physical timers or watchdog. */
#include "prot_fixture.h"
static void report(unsigned id, unsigned before)
{ printf("S%02u core boundary: %s\n",id,failures==before?"PASS":"FAIL"); }
static void fault_scenario(unsigned id, const fault_code_t *codes, unsigned count)
{
    unsigned i, before=failures;
    for(i=0;i<count;++i) {
        harness_t h; h_run(&h);
        CHECK(prot_on_fault(&h.state,&h.faults,codes[i],0,CH_MODE_TRIP,0,1));
        CHECK(h.state.mode==TRIPPED && h.state.permit==0 && h.state.first.code==codes[i]);
        fault_clear(&h.faults,codes[i],0); h_step(&h,100,true);
        CHECK(h.state.mode==TRIPPED); h_ack(&h,101); CHECK(h.state.mode==RUN);
    }
    report(id,before);
}
static void power_cuts(void)
{
    settings_t old=fixture_settings(), next=old, stale=old, a, b;
    set_store_t st; ee_op_t op; uint8_t ee[4096], read=0;
    uint8_t oldraw[SETTINGS_SLOT_SIZE], newraw[SETTINGS_SLOT_SIZE];
    unsigned i, writes=0, before=failures; bool av,bv; int selected;
    memset(&st,0,sizeof(st)); memset(ee,0xFF,sizeof(ee));
    CHECK(set_pack(&old,oldraw)==RES_OK); memcpy(ee+0x40,oldraw,sizeof(oldraw));
    stale.sequence=6; stale.ch[0].trip_dC=900; CHECK(set_pack(&stale,ee+0x340)==RES_OK);
    next.ch[0].trip_dC=1100; next.ch[0].name[0]='X';
    CHECK(set_commit(&st,&next,&old,0)==RES_OK);
    memcpy(newraw,st.image,sizeof(newraw));
    for(i=0;i<2000 && st.phase!=STORE_DONE;++i) {
        /* Reboot at every boundary, including after each EEPROM byte write. */
        av=set_unpack(ee+0x40,24,24,&a)==RES_OK;
        bv=set_unpack(ee+0x340,24,24,&b)==RES_OK;
        selected=set_select(av,a.sequence,bv,b.sequence); CHECK(selected>=0);
        if(selected==0) CHECK(memcmp(ee+0x40,oldraw,402)==0);
        else if(selected==1) CHECK(memcmp(ee+0x340,newraw,402)==0);
        set_store_step(&st,true,true,read,&op);
        if(op.kind==EE_WRITE) { ee[op.address]=op.value; ++writes; }
        if(op.kind==EE_READ) read=ee[op.address];
    }
    CHECK(st.phase==STORE_DONE && writes==403);
    report(7,before);
}
static void epoch_scenarios(void)
{
    settings_t s=fixture_settings(), reboot=fixture_settings(); calibration_t c=fixture_cal();
    uint8_t raw[SETTINGS_SLOT_SIZE]; int32_t learned[MAX_CHANNELS]={0}; unsigned before=failures;
    s.ch[1]=s.ch[0]; c.baseline_nV[1]=3200000; c.tag[1]=CH_TYPE_K;
    CHECK(cal_complete(&c,&s)); CHECK(set_change_type(&s.ch[0],CH_TYPE_OFF)==RES_OK);
    CHECK(set_pack(&s,raw)==RES_OK && set_unpack(raw,24,24,&reboot)==RES_OK);
    s=reboot; CHECK(set_change_type(&s.ch[0],CH_TYPE_K)==RES_OK);
    s.ch[0].alarm_dC=800; s.ch[0].trip_dC=1000; s.ch[0].probe_limit_dC=12000;
    CHECK(s.ch[0].type_epoch==2 && !cal_complete(&c,&s));
    learned[0]=3200000; learned[1]=3200000; CHECK(cal_learn(&c,&s,learned)==RES_OK && cal_complete(&c,&s));
    report(27,before); before=failures;
    c=fixture_cal(); c.baseline_nV[0]=CAL_MISSING; c.tag[0]=0;
    CHECK(cal_validate(&c)==RES_OK); /* staged service REF calibration */
    s=fixture_settings(); CHECK(set_change_type(&s.ch[0],CH_TYPE_J)==RES_OK);
    s.ch[0].alarm_dC=800; s.ch[0].trip_dC=1000; s.ch[0].probe_limit_dC=12000;
    CHECK(!cal_complete(&c,&s)); CHECK(cal_learn(&c,&s,learned)==RES_OK && cal_complete(&c,&s));
    report(28,before);
}
void test_scenarios(void)
{
    harness_t h; result_t r; unsigned before, i;
    before=failures; h_init(&h); h_step(&h,0,true); CHECK(h.state.mode==START_LATCHED && !h.out.run_permission);
    h_ack(&h,1); CHECK(h.state.mode==RUN && h.out.window_remaining_ms==0);
    h_step(&h,2,true); CHECK(h.out.run_permission && h.out.window_remaining_ms==900); report(1,before);
    before=failures; h_run(&h);
    for(i=790;i<=1000;i+=10) { r=sample((temp_dC_t)i,2); prot_on_result(&h.state,0,&r,&h.cfg,2,1); }
    CHECK(h.state.mode==TRIPPED && h.state.first.channel==1 && h.state.first.value_dC==1000); report(2,before);
    before=failures; h_run(&h); r=sample(1000,2); prot_on_result(&h.state,0,&r,&h.cfg,2,1);
    h.scan.meas[0].temp_dC=981; h_step(&h,100,true); h_ack(&h,101); CHECK(h.out.ack_reason==ACK_R4_CHANNEL);
    h.scan.meas[0].temp_dC=980; h_step(&h,102,true); h_ack(&h,103); CHECK(h.state.mode==RUN); report(3,before);
    before=failures; h_init(&h); h.in.ack=true;
    for(i=0;i<500;i+=5) h_step(&h,i,true);
    CHECK(h.state.mode==START_LATCHED); h.in.ack=false; h_ack(&h,501); CHECK(h.state.mode==RUN); report(4,before);
    before=failures; h_run(&h); h_step(&h,902,false);
    CHECK(h.state.mode==TRIPPED && h.state.first.code==FC_G05_SCAN_DEADLINE);
    prot_on_fault(&h.state,&h.faults,FC_B05_ADC_STALLED,0,CH_MODE_TRIP,0,1); CHECK(fault_active(&h.faults,FC_B05_ADC_STALLED));
    report(5,before);
    before=failures; h_run(&h);
    /* Fake environment advances 500 ms without flow checkpoints and resets. */
    h.in.now_ms=502; prot_init(&h.state,true,true,false); fault_init(&h.faults);
    fault_raise(&h.faults,FC_G11_RESET_WDT,0); h_step(&h,502,false);
    CHECK(h.state.mode==START_LATCHED && !h.out.run_permission); report(6,before);
    power_cuts();
    before=failures; h_init(&h); h.cfg.ch[0].trip_dC=0; h_step(&h,0,true); h_ack(&h,1);
    CHECK(h.state.mode==CONFIG_LOCK && !h.out.run_permission); report(8,before);
    before=failures; h_run(&h); /* a recovered CRC read yields no bank fault */
    h_step(&h,100,true); CHECK(h.state.mode==RUN);
    prot_on_fault(&h.state,&h.faults,FC_B02_ADC_CRC,0,CH_MODE_TRIP,0,1);
    CHECK(h.state.mode==TRIPPED); report(9,before);
    { const fault_code_t codes[]={FC_B01_ADC_ID,FC_B03_ADC_READBACK,FC_B04_ADC_ERROR}; fault_scenario(10,codes,3); }
    { const fault_code_t codes[]={FC_B12_CJ_ONE,FC_B10_CJ_BOTH,FC_B11_CJ_DIFF}; fault_scenario(11,codes,3); }
    { const fault_code_t codes[]={FC_G08_ENGREF_LOST,FC_G09_ENGREF_TEST}; fault_scenario(12,codes,2); }
    { const fault_code_t code=FC_B13_SIGNATURE; fault_scenario(13,&code,1); }
    before=failures;
    for(i=0;i<2;++i) {
        outputs_t o; prot_out_t p; output_decision_t d;
        memset(&o,0,sizeof(o)); memset(&p,0,sizeof(p)); h_run(&h);
        p.run_permission=i!=0; p.window_remaining_ms=900; p.alarm_active=true;
        (void)outputs_step(&o,&p,0,i!=0,true); (void)outputs_step(&o,&p,60,i!=0,true);
        d=outputs_step(&o,&p,161,i!=0,true); CHECK(d.run_fault==FC_G06_RUN_FEEDBACK);
        prot_on_fault(&h.state,&h.faults,d.run_fault,0,CH_MODE_TRIP,0,1); CHECK(h.state.mode==TRIPPED);
    }
    report(14,before);
    before=failures; h_run(&h);
    for(i=0;i<10000;++i) { /* simulated unrelated communications workload */
        r=sample(i<9999?999:1000,2); prot_on_result(&h.state,0,&r,&h.cfg,2,1);
    }
    CHECK(h.state.mode==TRIPPED && h.state.first.value_dC==1000); report(15,before);
    before=failures; h_run(&h); h.in.commit_begin=true; h.in.protection_change=true; h_step(&h,3,false);
    CHECK(h.state.mode==START_LATCHED && !h.out.run_permission); report(16,before);
    before=failures; h_run(&h); h.in.writing=true;
    for(i=100;i<3000;i+=100) h_step(&h,i,true);
    CHECK(h.state.mode==RUN && h.out.run_permission);
    ++h.cfg.sequence; h.in.writing=false; h.in.commit_done=true;
    h_step(&h,3100,true); CHECK(h.state.mode==RUN && h.out.window_refresh);
    report(17,before);
    before=failures; h_init(&h); h.cfg.ch[0].mode=CH_MODE_ALARM_ONLY;
    h.scan.meas[0].temp_dC=1100; h_step(&h,0,true); h_ack(&h,1); h_step(&h,2,true);
    CHECK(h.state.mode==RUN && h.out.alarm_active); report(18,before);
    before=failures; h_run(&h); h.scan.meas[1].flags=MEAS_OPEN; h_step(&h,3,true);
    CHECK(h.state.mode==RUN && !h.out.alarm_active); report(19,before);
    before=failures; h_run(&h); r=sample(1100,2); prot_on_result(&h.state,0,&r,&h.cfg,2,1);
    CHECK(h.state.mode==TRIPPED); report(20,before);
    before=failures; h_run(&h);
    prot_on_fault(&h.state,&h.faults,FC_B06_REF,0,CH_MODE_TRIP,0,1);
    prot_on_fault(&h.state,&h.faults,FC_B06_REF,1,CH_MODE_TRIP,0,1);
    fault_clear(&h.faults,FC_B06_REF,0); CHECK(fault_active(&h.faults,FC_B06_REF));
    h_ack(&h,4); CHECK(h.state.mode==TRIPPED && h.out.ack_reason==ACK_R3_FAULT); report(21,before);
    before=failures; h_run(&h); r=sample(100,2); r.flags=MEAS_RANGE;
    prot_on_result(&h.state,0,&r,&h.cfg,2,1); CHECK(h.state.mode==TRIPPED);
    h.scan.meas[0]=r; h.scan.scan_no=2; h_ack(&h,10); CHECK(h.out.ack_reason==ACK_R4_CHANNEL);
    h.scan.meas[0]=sample(100,3); h.scan.scan_no=3; h_step(&h,11,true); h_ack(&h,12);
    CHECK(h.state.mode==RUN); report(22,before);
    before=failures; h_run(&h); h.in.commit_begin=true; h.in.protection_change=true; h_step(&h,3,false);
    h.in.commit_begin=false; ++h.cfg.sequence; h.in.commit_done=true; h_step(&h,4,false);
    h.in.commit_done=false; h_ack(&h,5); CHECK(h.out.ack_reason==ACK_R2_SCAN); report(23,before);
    { const fault_code_t code=FC_G14_ISLAND_LOST; fault_scenario(24,&code,1); }
    { const fault_code_t code=FC_G05_SCAN_DEADLINE; fault_scenario(25,&code,1); }
    before=failures; h_run(&h); h_step(&h,902,false); h_step(&h,952,true);
    CHECK(h.state.mode==TRIPPED && !h.out.run_permission); report(26,before);
    epoch_scenarios();
}
