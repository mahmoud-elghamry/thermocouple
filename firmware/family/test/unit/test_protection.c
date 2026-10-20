#include "prot_fixture.h"
static void ack_rules(void)
{
    harness_t h;
    h_init(&h); h.in.ack=true; h_step(&h,0,true); CHECK(h.out.ack_reason==ACK_R1_RELEASE);
    h_init(&h); h.in.ack_held_ms=49; h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R1_RELEASE);
    h_init(&h); h.in.ack_age_ms=501; h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R1_RELEASE);
    h_init(&h); h.scan.scan_validated=false; h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R2_SCAN);
    h_init(&h); h_ack(&h,1000); CHECK(h.out.ack_reason==ACK_R2_SCAN);
    h_init(&h); h.scan.settings_seq--; h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R2_SCAN);
    h_init(&h); fault_raise(&h.faults,FC_B06_REF,1); h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R3_FAULT);
    h_init(&h); h.scan.meas[0].temp_dC=981; h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R4_CHANNEL);
    h_init(&h); h.in.writing=true; h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R5_SETTINGS);
    h_init(&h); h.in.readback_off_ok=false; h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R6_RELAY);
    h_init(&h); h.scan.meas[0].temp_dC=980; h_ack(&h,1); CHECK(h.state.mode==RUN);
    h_init(&h); h.in.ack_age_ms=500; h_ack(&h,999); CHECK(h.state.mode==RUN);
    h_init(&h); h.scan.bank[0]=(bank_status_t)99; h_ack(&h,1); CHECK(h.out.ack_reason==ACK_R2_SCAN);
    h_init(&h); h.cfg.ch[0].mode=CH_MODE_ALARM_ONLY; h.scan.meas[0].flags=MEAS_OPEN;
    h_ack(&h,1); CHECK(h.state.mode==RUN && h.out.alarm_active);
}
static void off_faults(void)
{
    static const fault_code_t codes[]={FC_C01_OPEN,FC_C02_RANGE,FC_C03_COMMON_MODE,
        FC_C06_SHORTED,FC_C07_OVUV,FC_C08_COLD,FC_C09_RTD};
    harness_t h; unsigned i;
    for(i=0;i<sizeof(codes)/sizeof(codes[0]);++i) {
        h_run(&h); fault_raise(&h.faults,codes[i],1); h_step(&h,3,false);
        CHECK(h.state.mode==RUN && !h.out.alarm_active);
        h_ack(&h,4); CHECK(h.state.mode==RUN && h.out.ack_reason==ACK_NONE && !h.out.alarm_active);
        /* Recovered but unacknowledged C latches must also be ignored on OFF. */
        fault_clear(&h.faults,codes[i],1); h_step(&h,5,false); CHECK(!h.out.alarm_active);
        h.state.alarm_latch[1]=1; h_step(&h,6,false); CHECK(!h.out.alarm_active);
        prot_on_fault(&h.state,&h.faults,codes[i],1,CH_MODE_TRIP,2,0);
        h_step(&h,7,false); CHECK(h.state.mode==RUN && !h.out.alarm_active);
        /* The same registry latch on a fitted channel survives recovery until ACK. */
        h_run(&h); h.cfg.ch[0].mode=CH_MODE_ALARM_ONLY;
        fault_raise(&h.faults,codes[i],0); fault_clear(&h.faults,codes[i],0);
        h_step(&h,3,false); CHECK(h.out.alarm_active);
        h_ack(&h,4); CHECK(!h.out.alarm_active);
    }
}
static void window_sequences(void)
{
    harness_t h; unsigned tag;
    /* Entering RUN in this pass cannot use this pass's completion for PWM. */
    h_init(&h); h.in.ack_key_released=true; h_step(&h,0,false);
    h.in.ack_key_released=false; h.in.ack=true; h_step(&h,1,true);
    CHECK(h.state.mode==RUN && !h.out.window_refresh && h.out.window_remaining_ms==0);
    h.in.ack=false; h_step(&h,2,true); CHECK(h.out.window_refresh);
    /* An unannounced active change accepts neither its own nor the former tag. */
    for(tag=0;tag<2;++tag) {
        h_run(&h); ++h.cfg.sequence;
        if(tag) h.scan.settings_seq=h.cfg.sequence;
        h_step(&h,500,true); CHECK(!h.out.window_refresh);
        h_step(&h,902,false); CHECK(h.state.mode==TRIPPED && !h.out.run_permission);
    }
    /* 04 section 6.1: the names-only exception covers only the sequence just
     * replaced. A scan older than a missed save must not move the deadline. */
    h_run(&h); ++h.cfg.sequence; h_step(&h,3,false);
    ++h.cfg.sequence; h.in.commit_done=true; h_step(&h,4,true); CHECK(!h.out.window_refresh);
    CHECK(h.state.window_started_ms==2 && h.out.window_remaining_ms==898);
    /* 04 section 6.1 permits the just-replaced tag; after an unseen save the
     * implementation safely requires new-sequence proof instead (05 section 5
     * increments once per save). Keep this stricter refusal explicit. */
    h.in.commit_done=false; ++h.scan.settings_seq; h_step(&h,5,true); CHECK(!h.out.window_refresh);
    CHECK(h.state.window_started_ms==2 && h.out.window_remaining_ms==897);
    h.scan.settings_seq=h.cfg.sequence; h_step(&h,6,true); CHECK(h.out.window_refresh);
    /* A names-only commit admits exactly the replaced sequence, until new proof. */
    h_run(&h); ++h.cfg.sequence; h.in.commit_done=true;
    h_step(&h,100,true); CHECK(h.state.mode==RUN && h.out.window_refresh);
    h.in.commit_done=false; h_step(&h,200,true); CHECK(h.out.window_refresh);
    h.scan.settings_seq=h.cfg.sequence; h_step(&h,300,true); CHECK(h.out.window_refresh);
    --h.scan.settings_seq; h_step(&h,400,true); CHECK(!h.out.window_refresh);
    /* A second commit replaces only the immediately preceding accepted sequence. */
    ++h.cfg.sequence; h.in.commit_done=true; h_step(&h,500,true); CHECK(!h.out.window_refresh);
    h.in.commit_done=false; ++h.scan.settings_seq; h_step(&h,600,true); CHECK(h.out.window_refresh);
    h.scan.settings_seq=h.cfg.sequence; h_step(&h,700,true); CHECK(h.out.window_refresh);
    /* Sequence zero is an ordinary accepted value after unsigned wrap. */
    h_init(&h); h.cfg.sequence=UINT32_MAX; h.scan.settings_seq=UINT32_MAX;
    h_ack(&h,1); h_step(&h,2,true); CHECK(h.out.window_refresh);
    h.cfg.sequence=0; h.in.commit_done=true; h_step(&h,3,true); CHECK(h.out.window_refresh);
    h.in.commit_done=false; h.scan.settings_seq=0; h_step(&h,4,true); CHECK(h.out.window_refresh);
    h.scan.settings_seq=UINT32_MAX; h_step(&h,5,true); CHECK(!h.out.window_refresh);
}
void test_protection(void)
{
    harness_t h; result_t r; unsigned mode;
    ack_rules(); off_faults(); window_sequences(); h_init(&h);
    prot_init(&h.state,false,false,false); CHECK(h.state.mode==CONFIG_LOCK);
    h.in.settings_valid=false; h_ack(&h,1); CHECK(h.state.mode==CONFIG_LOCK);
    h.in.commit_begin=true; h.in.protection_change=true; h_step(&h,2,false); CHECK(h.state.mode==CONFIG_LOCK);
    prot_init(&h.state,false,false,true); h_step(&h,2,false); CHECK(h.state.mode==SERVICE);
    h_init(&h); prot_init(&h.state,false,false,false);
    h.in.commit_done=true; h_step(&h,1,false); CHECK(h.state.mode==START_LATCHED);
    h_run(&h); r=sample(1000,2);
    CHECK(prot_on_result(&h.state,0,&r,&h.cfg,2,20));
    CHECK(h.state.mode==TRIPPED && h.state.permit==0 && h.state.first.code==FC_C10_OVER_TRIP);
    CHECK(h.state.first.channel==1 && h.state.first.value_dC==1000 && h.state.first.threshold_dC==1000);
    prot_on_fault(&h.state,&h.faults,FC_B01_ADC_ID,1,CH_MODE_TRIP,0,21);
    CHECK(h.state.first.code==FC_C10_OVER_TRIP);
    fault_clear(&h.faults,FC_B01_ADC_ID,1); h_step(&h,3,true); h_ack(&h,4);
    CHECK(h.state.mode==RUN && !h.state.first.valid);
    for(mode=START_LATCHED;mode<=TRIPPED;++mode) {
        h_init(&h); h.state.mode=(prot_mode_t)mode; h.state.mode_inv=(uint8_t)~mode;
        h.state.permit=(mode==RUN)?1:0; h.state.permit_inv=(uint8_t)~h.state.permit;
        h.in.commit_begin=true; h.in.protection_change=true; h_step(&h,1,false);
        CHECK(h.state.mode==START_LATCHED && !h.out.run_permission);
    }
    h_run(&h); h.in.commit_begin=true; h.in.protection_change=false; h_step(&h,3,false);
    CHECK(h.state.mode==RUN);
    h_run(&h); h.in.settings_valid=false; h_step(&h,3,false); CHECK(h.state.mode==CONFIG_LOCK);
    h_run(&h); prot_on_fault(&h.state,&h.faults,FC_G01_SETTINGS_INVALID,0,CH_MODE_TRIP,0,1);
    CHECK(h.state.mode==CONFIG_LOCK);
    h_run(&h); prot_on_fault(&h.state,&h.faults,FC_G10_CALIBRATION,0,CH_MODE_TRIP,0,1);
    CHECK(h.state.mode==CONFIG_LOCK);
    h_run(&h); h.state.mode=(prot_mode_t)99; h_step(&h,3,false);
    CHECK(h.state.mode==TRIPPED && fault_active(&h.faults,FC_G04_INTERNAL));
    h_run(&h); h.state.permit_inv^=1; h_step(&h,3,false); CHECK(h.state.mode==TRIPPED);
    h_run(&h); h.state.mode_inv^=1; h_step(&h,3,false); CHECK(h.state.mode==TRIPPED);
    h_run(&h); h_step(&h,902,false);
    CHECK(h.state.mode==TRIPPED && h.state.first.code==FC_G05_SCAN_DEADLINE);
    h_step(&h,950,true); CHECK(h.state.mode==TRIPPED && !h.out.run_permission);
    h_run(&h); h_step(&h,901,false); CHECK(h.state.mode==RUN && h.out.window_remaining_ms==1);
    h_run(&h); h.in.flow_ok=false; h_step(&h,3,false); CHECK(!h.out.run_permission);
    /* Alarm latch clears only on fresh ACK after reset-band clearance. */
    h_run(&h); h.scan.meas[0].temp_dC=800; h_step(&h,3,true); CHECK(h.out.alarm_active);
    h.scan.meas[0].temp_dC=781; h_ack(&h,4); CHECK(h.out.alarm_active);
    h.scan.meas[0].temp_dC=780; h_ack(&h,5); CHECK(!h.out.alarm_active);
    /* Already raised faults must still trip on immediate notification. */
    h_run(&h); fault_raise(&h.faults,FC_B01_ADC_ID,0);
    prot_on_fault(&h.state,&h.faults,FC_B01_ADC_ID,0,CH_MODE_TRIP,0,1);
    CHECK(h.state.mode==TRIPPED);
    /* An active channel fault cannot be ACKed using an older good sample. */
    h_run(&h); prot_on_fault(&h.state,&h.faults,FC_C01_OPEN,0,CH_MODE_TRIP,1,1);
    h_ack(&h,3); CHECK(h.out.ack_reason==ACK_R4_CHANNEL && h.state.mode==TRIPPED);
    fault_clear(&h.faults,FC_C01_OPEN,0); h_ack(&h,4); CHECK(h.state.mode==RUN);
    h_init(&h); h.cfg.ch[0].mode=CH_MODE_ALARM_ONLY; fault_raise(&h.faults,FC_C01_OPEN,0);
    h_ack(&h,1); CHECK(h.state.mode==RUN && h.out.alarm_active);
    /* First-out is absent until a trip/failed startup ACK, and remains oldest. */
    h_init(&h); r=sample(1100,1); prot_on_result(&h.state,0,&r,&h.cfg,1,1);
    CHECK(!h.state.first.valid && h.state.mode==START_LATCHED);
    h.scan.meas[0]=r; h_ack(&h,1); CHECK(h.state.first.valid && h.state.first.code==FC_C10_OVER_TRIP);
    /* Unsigned elapsed-time arithmetic works across ms_tick rollover. */
    h_run(&h); h.state.window_started_ms=UINT32_MAX-100u;
    h_step(&h,798,false); CHECK(h.state.mode==RUN && h.out.window_remaining_ms==1);
    h_step(&h,799,false); CHECK(h.state.mode==TRIPPED);
    /* A queued press cannot grant RUN on the same loop as a protection edit. */
    h_run(&h); h.in.ack_key_released=true; h_step(&h,3,false);
    h.in.ack_key_released=false; h.in.ack=true; h.in.commit_begin=true; h.in.protection_change=true;
    h_step(&h,4,false); CHECK(h.state.mode==START_LATCHED && h.out.ack_reason==ACK_R1_RELEASE);
}
