#include "app/app.h"
#include "app/ack_input.h"
#include "app/outputs_hw.h"
#include "app/service.h"
#include "app/ee_owner.h"
#include "drivers/keys.h"
#include "drivers/lcd.h"
#include "drivers/ad7124.h"
#include "app/acquisition_budget.h"
#include "drivers/relays.h"
#include "services/scan.h"
#include "mcal/timer.h"
#include "fake_hw.h"
#include "model.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
unsigned settings_validation_count(void);
static void fail(unsigned line,const char *expr) {
    uint8_t unit; fault_code_t cause=fault_first_trip(app_faults(),&unit);
    printf("review FAIL %u: %s mode=%u ack=%u active=%u/%u\n",line,expr,f0_mode(),app_ack_reason(),cause,unit); exit(1);
}
#define CHECK(x) do { ++checks; if(!(x)) fail(__LINE__,#x); } while(0)
static void loop(unsigned n) { unsigned i; for(i=0;i<n;i++) { f0_task(); fake_advance(1); } CHECK(!model_watchdog_reset()); }
static void setup(bool service) {
    settings_t cfg; calibration_t cal; uint8_t bytes[SETTINGS_SLOT_SIZE]; unsigned i;
    fake_reset(); memset(&cfg,0,sizeof cfg); memset(&cal,0,sizeof cal);
    cfg.board_type=cfg.channel_count=24; cfg.address=1; cfg.sequence=7; cal.bank_count=3;
    for(i=0;i<MAX_CHANNELS;i++) { memcpy(cfg.ch[i].name,"      ",6); cfg.ch[i].band_C=2; cal.baseline_nV[i]=CAL_MISSING; }
    cfg.ch[0].type=CH_TYPE_K; cfg.ch[0].alarm_dC=800; cfg.ch[0].trip_dC=1000; cfg.ch[0].probe_limit_dC=12000;
    cal.baseline_nV[0]=3200000; cal.tag[0]=1;
    CHECK(set_pack(&cfg,bytes)==RES_OK); memcpy(fake_eeprom+0x40,bytes,sizeof bytes);
    CHECK(cal_pack(&cal,bytes)==RES_OK); memcpy(fake_eeprom+0x640,bytes,CAL_SLOT_SIZE);
    fake_pin(board()->keys[2],!service); f0_init(); loop(3000);
}
static void ack(void) {
    fake_pin(board()->keys[3],true); loop(20); fake_pin(board()->keys[3],false); loop(70);
    fake_pin(board()->keys[3],true); loop(20);
}
static void timestamp(void) {
    prot_in_t in; memset(&in,0,sizeof in); setup(false); keys_init(); ack_input_init();
    fake_advance(10); keys_task(); ack_input_step(&in);
    fake_pin(board()->keys[3],false); fake_advance(8); keys_task();
    fake_advance(1); ack_input_step(&in); /* tick between driver and adapter */
    fake_advance(49); keys_task(); ack_input_step(&in);
    CHECK(in.ack && in.ack_held_ms==50 && in.ack_age_ms==0);
    fake_pin(board()->keys[3],true); keys_init(); ack_input_init();
    fake_advance(10); keys_task(); ack_input_step(&in);
    fake_pin(board()->keys[3],false); fake_advance(8); keys_task();
    fake_advance(50); keys_task(); fake_advance(7); ack_input_step(&in);
    CHECK(in.ack && in.ack_held_ms==50 && in.ack_age_ms==7);
}
static void expiry(void) {
    unsigned i;
    setup(false); ack(); loop(750); CHECK(timer_run_active());
    timer_run_start(1); fake_advance(1); CHECK(!timer_run_active());
    outputs_hw_apply(true,true,900); CHECK(!timer_run_active());
    loop(1); CHECK(f0_mode()==TRIPPED && fault_latched_at(app_faults(),FC_G05_SCAN_DEADLINE,0));
    loop(1500); CHECK(!timer_run_active()); ack(); CHECK(f0_mode()==RUN); loop(750); CHECK(timer_run_active());
    model_expire_on_grant(); loop(750);
    CHECK(f0_mode()==TRIPPED && !timer_run_active());
    CHECK(fault_latched_at(app_faults(),FC_G05_SCAN_DEADLINE,0));
    for(i=0;i<800 && fault_active(app_faults(),FC_G05_SCAN_DEADLINE);i++) loop(1);
    CHECK(i<800 && !timer_run_active()); /* Cleared scan evidence alone cannot restart. */
    ack(); CHECK(f0_mode()==RUN); loop(750); CHECK(timer_run_active());
}
static void service_key(bool escape) {
    fake_pin(board()->keys[escape?0:2],false); if(escape) fake_pin(board()->keys[1],false);
    loop(30); fake_pin(board()->keys[0],true); fake_pin(board()->keys[1],true); fake_pin(board()->keys[2],true); loop(220);
}
static void service_abort(void) {
    unsigned step,key,i; settings_t candidate;
    for(step=2;step<=4;step++) for(key=0;key<4;key++) {
        setup(true); fake_pin(board()->keys[2],true); loop(9000); CHECK(svc_active_step()==1);
        for(i=1;i<step;i++) service_key(true);
        CHECK(svc_active_step()==step); service_key(false);
        CHECK(step==2?relay_alarm_sense():step==3?timer_run_active():(fake_port(PORT_B)&8)!=0);
        if(step==3 && key==2) {
            candidate=*app_settings(); candidate.ch[0].name[0]='X';
            CHECK(app_commit_settings(&candidate)==RES_OK);
            fake_pin(board()->keys[key],false); fake_advance(8); loop(1);
            CHECK(ee_owner_busy()); /* Commit notice and press in this pass. */
        } else { fake_pin(board()->keys[key],false); loop(9); }
        CHECK(!timer_run_active() && !(fake_port(PORT_B)&8) && !relay_alarm_sense());
        CHECK(svc_active_step()==step+1); /* Still held: no release gesture. */
    }
}
static void adc_verifier(void) {
    setup(false); fake_ad_reg(0,5,0);
    CHECK(ad_verify_mutable_part(0,17)==RES_ERR_ID);
    CHECK(ad_fault(0)==FC_B01_ADC_ID);
}
static void cj_budget(void) {
    unsigned i; uint32_t bytes,hardware,start;
    setup(false); start=scan_last()->scan_no;
    for(i=0;i<1600;i++) {
        bytes=fake_soft_bytes; hardware=fake_spi_bytes; f0_task();
        CHECK(fake_spi_bytes-hardware<=64); /* Poll all banks, process one completion. */
        CHECK(fake_soft_bytes-bytes<=12); /* One frame, including one CRC retry. */
        fake_advance(1);
    }
    CHECK(scan_last()->scan_no>=start+2 && scan_last()->scan_validated);
}
static void blank(void) {
    fake_reset(); f0_init(); loop(3000); CHECK(f0_mode()==CONFIG_LOCK && !timer_run_active());
    fake_reset(); fake_pin(board()->keys[2],false); f0_init(); loop(3000); CHECK(f0_mode()==SERVICE);
    setup(false); fake_eeprom[0x640]=0; f0_init(); loop(3000);
    CHECK(f0_mode()==CONFIG_LOCK && !timer_run_active());
}
static void validation_budget(void) {
    unsigned i,completed=0; uint32_t last; settings_t cfg; calibration_t cal; uint8_t bytes[SETTINGS_SLOT_SIZE];
    setup(false); cfg=*app_settings(); memset(&cal,0,sizeof cal); cal.bank_count=3;
    for(i=0;i<MAX_CHANNELS;i++) cal.baseline_nV[i]=CAL_MISSING;
    for(i=0;i<24;i++) { cfg.ch[i]=cfg.ch[0]; cal.baseline_nV[i]=3200000; cal.tag[i]=1; }
    CHECK(set_pack(&cfg,bytes)==RES_OK); memcpy(fake_eeprom+0x40,bytes,sizeof bytes);
    CHECK(cal_pack(&cal,bytes)==RES_OK); memcpy(fake_eeprom+0x640,bytes,CAL_SLOT_SIZE);
    f0_init(); loop(3000); last=scan_last()->scan_no;
    for(i=0;i<1600;i++) {
        (void)settings_validation_count(); f0_task();
        CHECK(settings_validation_count()==1);
        if(scan_last()->scan_no!=last) { ++completed; last=scan_last()->scan_no; }
        fake_advance(1);
    }
    CHECK(completed>=2);
}
static void event_cursor(void) {
    settings_t cfg; calibration_t cal; events_t expected; event_t e; unsigned i;
    setup(false); cfg=*app_settings(); memset(&cal,0,sizeof cal); cal.bank_count=3;
    fake_reset(); memset(&e,0,sizeof e); e.type=EV_ACK;
    for(i=0;i<EVENT_SLOTS;i++) {
        e.sequence=(uint16_t)(0xFFF0u+i); CHECK(ev_pack(&e,expected.slot[i])==RES_OK);
    }
    expected.slot[31][15]^=1; /* Torn newest slot; sequence wraps in the ring. */
    memcpy(fake_eeprom+0x840,&expected,sizeof expected);
    ee_owner_init(&cfg,&cal,0,0,true);
    for(i=0;i<2;i++) {
        e.type=EV_ALARM; e.code=FC_C11_OVER_ALARM; e.power_cycles=1;
        CHECK(ee_owner_log(&e)); CHECK(ev_log(&expected,&e)>=0);
    }
    for(i=0;i<300 && !ee_owner_events_drained();i++) { ee_owner_step(); fake_advance(4); }
    CHECK(i<300 && memcmp(fake_eeprom+0x840,&expected,sizeof expected)==0);
}
static void lcd_budget(void) {
    char frame[80]; setup(false); memset(frame,'X',sizeof frame); lcd_frame(frame);
    model_loop_begin(); lcd_task(); CHECK(model_loop_us()<=100);
}
static void ready_stamp(void) {
    unsigned i; uint32_t code;
    setup(false); ad_reset_state();
    for(i=0;i<1000;i++) { res_t r=ad_init(0); if(r==RES_OK) break; CHECK(r==RES_BUSY); fake_advance(1); }
    CHECK(i<1000); ad_scan_begin(0,7);
    CHECK(ad_start_slot(0,0)==RES_OK); fake_advance(43); CHECK(ad_ready(0)==RES_OK);
    fake_advance(30); CHECK(ad_poll(0,&code)==RES_OK); /* DATA held; first RDY was in range. */
    CHECK(ad_start_slot(0,0)==RES_OK); fake_advance(43); CHECK(ad_ready(0)==RES_OK);
    fake_ad_por(0,true); fake_advance(20);
    CHECK(ad_poll(0,&code)==RES_ERR_READBACK && ad_fault(0)==FC_B15_ADC_RESET);
}
static void protection_cache(void) {
    prot_state_t plain,prepared; prot_out_t a,b; prot_in_t in;
    fault_registry_t fa,fb; unsigned ch;
    setup(false); memset(&in,0,sizeof in); fault_init(&fa); fault_init(&fb);
    prot_init(&plain,true,true,false); prot_init(&prepared,true,true,false);
    in.settings=app_settings(); in.scan=scan_last(); in.now_ms=tick_ms();
    in.settings_valid=in.calibration_valid=in.flow_ok=true; in.scan_complete=true;
    for(ch=0;ch<24;ch++) {
        (void)prot_on_result(&plain,(uint8_t)ch,&in.scan->meas[ch],in.settings,in.scan->scan_no,0);
        (void)prot_on_result(&prepared,(uint8_t)ch,&in.scan->meas[ch],in.settings,in.scan->scan_no,0);
    }
    in.faults=&fa; prot_step(&in,&plain,&a);
    in.faults=&fb; in.results_evaluated=true; prot_step(&in,&prepared,&b);
    CHECK(memcmp(&a,&b,sizeof a)==0 && memcmp(&plain,&prepared,sizeof plain)==0);
    in.scan_complete=false; in.results_evaluated=false;
    in.faults=&fa; prot_step(&in,&plain,&a);
    in.faults=&fb; in.scan_unchanged=true; prot_step(&in,&prepared,&b);
    CHECK(memcmp(&a,&b,sizeof a)==0 && memcmp(&plain,&prepared,sizeof plain)==0);
    in.ack_key_released=true; in.readback_off_ok=true;
    in.faults=&fa; in.scan_unchanged=false; prot_step(&in,&plain,&a);
    in.faults=&fb; in.scan_unchanged=true; prot_step(&in,&prepared,&b);
    in.ack=true; in.ack_held_ms=50;
    in.faults=&fa; in.scan_unchanged=false; prot_step(&in,&plain,&a);
    in.faults=&fb; in.scan_unchanged=true; prot_step(&in,&prepared,&b);
    CHECK(a.run_permission && b.run_permission && memcmp(&a,&b,sizeof a)==0);
    CHECK(memcmp(&plain,&prepared,sizeof plain)==0);
    /* Notification-only revision hint changes on activation/clear, not repeat
     * calls. The real registry bitmaps remain authoritative for protection. */
    { uint32_t rev=fa.active_revision;
      CHECK(fault_raise(&fa,FC_C01_OPEN,0) && fa.active_revision==rev+1u);
      CHECK(!fault_raise(&fa,FC_C01_OPEN,0) && fa.active_revision==rev+1u);
      fault_clear(&fa,FC_C01_OPEN,0); CHECK(fa.active_revision==rev+2u);
      fault_clear(&fa,FC_C01_OPEN,0); CHECK(fa.active_revision==rev+2u);
    }
}
void test_review(void) {
    timestamp(); lcd_budget(); ready_stamp(); protection_cache(); cj_budget(); expiry(); service_abort(); blank(); validation_budget(); event_cursor(); adc_verifier();
    printf("Astra review: %u checks PASS\n",checks);
}
