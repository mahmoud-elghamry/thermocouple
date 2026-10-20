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
void test_protection(void)
{
    harness_t h; result_t r; unsigned mode;
    ack_rules(); h_init(&h);
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
