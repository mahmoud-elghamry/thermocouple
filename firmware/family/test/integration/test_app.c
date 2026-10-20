#include "app/app.h"
#include "app/ee_owner.h"
#include "app/service.h"
#include "services/scan.h"
#include "services/tc_math.h"
#include "drivers/keys.h"
#include "mcal/timer.h"
#include "mcal/wdt.h"
#include "fake_hw.h"
#include "model.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
static uint32_t worst_us;
#define CHECK(x) do { ++checks; if(!(x)) { printf("integration FAIL %d: %s mode=%u t=%lu\n",__LINE__,#x,f0_mode(),(unsigned long)tick_ms()); exit(1); } } while(0)
static void loop(unsigned n) {
    unsigned i; for(i=0;i<n;i++) {
        uint32_t elapsed; model_loop_begin(); f0_task(); elapsed=model_loop_us();
        if(elapsed>worst_us) worst_us=elapsed;
        CHECK(elapsed<=8000); CHECK(!model_watchdog_reset()); fake_advance(1);
    }
}
static settings_t cfg;
static calibration_t cal;
static void fixture(void) {
    uint8_t bytes[SETTINGS_SLOT_SIZE]; unsigned c;
    memset(&cfg,0,sizeof cfg); memset(&cal,0,sizeof cal);
    cfg.board_type=24; cfg.channel_count=24; cfg.address=1; cfg.sequence=7; cal.bank_count=3;
    /* Explicit TEST limits, never commissioning defaults. */
    for(c=0;c<MAX_CHANNELS;c++) { memcpy(cfg.ch[c].name,"      ",6); cfg.ch[c].band_C=2; cal.baseline_nV[c]=CAL_MISSING; }
    cfg.ch[0].type=CH_TYPE_K; cfg.ch[0].alarm_dC=800; cfg.ch[0].trip_dC=1000; cfg.ch[0].probe_limit_dC=12000;
    cal.baseline_nV[0]=3200000; cal.tag[0]=1;
    CHECK(set_pack(&cfg,bytes)==RES_OK); memcpy(fake_eeprom+0x40,bytes,SETTINGS_SLOT_SIZE);
    CHECK(cal_pack(&cal,bytes)==RES_OK); memcpy(fake_eeprom+0x640,bytes,CAL_SLOT_SIZE);
}
static void boot(bool held) {
    fake_reset(); fixture(); fake_pin(board()->keys[3],!held); f0_init(); loop(3000);
    CHECK(f0_mode()==START_LATCHED); CHECK(!timer_run_active());
}
static void ack(void) {
    fake_pin(board()->keys[3],true); loop(20);
    fake_pin(board()->keys[3],false); loop(70);
    fake_pin(board()->keys[3],true); loop(20);
}
static void running(void) { boot(false); ack(); CHECK(f0_mode()==RUN); loop(750); CHECK(timer_run_active()); }
static void temperature(temp_dC_t t) {
    emf_nV_t hot,cold; int64_t code;
    CHECK(tc_dC_to_emf(CH_TYPE_K,t,&hot)==RES_OK);
    CHECK(tc_dC_to_emf(CH_TYPE_K,250,&cold)==RES_OK);
    code=0x800000LL+(int64_t)(hot-cold)*32*8388608/2500000000LL;
    fake_ad_code(0,0,(uint32_t)code);
    fake_ad_code(0,14,(uint32_t)(code+343597));
}
static void safety(void) {
    unsigned phase; uint32_t worst=0,start,elapsed;
    boot(false); fake_pin(board()->keys[3],false);
    for(phase=0;phase<100 && f0_mode()!=RUN;phase++) loop(1);
    CHECK(f0_mode()==RUN && !timer_run_active()); start=scan_last()->scan_no;
    fake_pin(board()->keys[3],true);
    for(phase=0;phase<800 && scan_last()->scan_no==start;phase++) { CHECK(!timer_run_active()); loop(1); }
    CHECK(phase<800 && timer_run_active());
    running(); temperature(850); loop(750);
    CHECK(f0_mode()==RUN && timer_run_active() && app_output()->alarm_active);
    boot(true); loop(1000); CHECK(f0_mode()==START_LATCHED); ack(); CHECK(f0_mode()==RUN);
    for(phase=0;phase<700;phase+=25) {
        running(); loop(phase); start=tick_ms(); temperature(1100);
        for(elapsed=0;elapsed<1000 && timer_run_active();elapsed++) loop(1);
        elapsed=tick_ms()-start; if(elapsed>worst) worst=elapsed;
        CHECK(!timer_run_active()); CHECK(elapsed<=1000); CHECK(f0_mode()==TRIPPED);
        CHECK(app_protection()->first.code==FC_C10_OVER_TRIP);
    }
    printf("S02 crossing-to-PWM-off worst: %lu ms (28 phases)\n",(unsigned long)worst);
    temperature(990); loop(1500); ack(); CHECK(f0_mode()==TRIPPED); CHECK(app_ack_reason()==ACK_R4_CHANNEL);
    temperature(950); loop(1500); ack(); CHECK(f0_mode()==RUN); CHECK(!timer_run_active()); loop(750); CHECK(timer_run_active());
    running(); fake_ad_ready(0,60000); start=tick_ms();
    for(elapsed=0;elapsed<901 && timer_run_active();elapsed++) loop(1);
    CHECK(!timer_run_active()); CHECK(f0_mode()==TRIPPED);
    CHECK(tick_ms()-start<=900);
    printf("S05 stalled-ADC-to-PWM-off: %lu ms\n",(unsigned long)(tick_ms()-start));
    loop(1000);
    CHECK(fault_latched_at(app_faults(),FC_B05_ADC_STALLED,0));
    CHECK(fault_latched_at(app_faults(),FC_G05_SCAN_DEADLINE,0));
}
static void injected(void) {
    unsigned i;
    running(); fake_ad_crc(0,1); loop(700); CHECK(f0_mode()==RUN && timer_run_active());
    fake_ad_crc(0,255); loop(200); CHECK(f0_mode()==TRIPPED && !timer_run_active());
    CHECK(fault_latched_at(app_faults(),FC_B02_ADC_CRC,0));
    for(i=0;i<3;i++) {
        running();
        if(i==0) fake_ad_reg(0,5,0);
        if(i==1) fake_ad_reg(0,0x19,0);
        if(i==2) fake_ad_error(0,1);
        loop(850); CHECK(f0_mode()==TRIPPED && !timer_run_active());
        CHECK(fault_latched_at(app_faults(),i==0?FC_B01_ADC_ID:i==1?FC_B03_ADC_READBACK:FC_B04_ADC_ERROR,0));
    }
    for(i=0;i<3;i++) {
        running(); fake_tmp_reg(0,12,0);
        if(i==1) fake_tmp_reg(1,12,0);
        if(i==2) { fake_tmp_reg(0,12,0x2126); fake_tmp_reg(0,0,0x0F00); }
        loop(850); CHECK(f0_mode()==TRIPPED && !timer_run_active());
        CHECK(fault_latched_at(app_faults(),i==0?FC_B12_CJ_ONE:i==1?FC_B10_CJ_BOTH:FC_B11_CJ_DIFF,0));
    }
    running(); fake_pin(board()->refok,true); loop(850);
    CHECK(f0_mode()==TRIPPED && fault_latched_at(app_faults(),FC_G08_ENGREF_LOST,0));
    fake_reset(); fixture(); fake_ref_follow=false; f0_init(); loop(3000);
    CHECK(!timer_run_active() && fault_latched_at(app_faults(),FC_G09_ENGREF_TEST,0));
    running();
    for(i=0;i<200;i++) { fake_pin(board()->run_sense,true); loop(1); }
    CHECK(f0_mode()==TRIPPED && fault_latched_at(app_faults(),FC_G06_RUN_FEEDBACK,0));
    boot(false);
    for(i=0;i<200;i++) { fake_pin(board()->run_sense,false); loop(1); }
    CHECK(!timer_run_active() && fault_latched_at(app_faults(),FC_G06_RUN_FEEDBACK,0));
}
static void commits(void) {
    settings_t candidate,old,newer; uint8_t image[4096]; unsigned cut,steps,new_seen=0;
    uint32_t writes;
    running(); candidate=*app_settings(); candidate.ch[0].trip_dC=1100; candidate.ch[0].alarm_dC=850;
    CHECK(app_commit_settings(&candidate)==RES_OK); loop(1);
    CHECK(!timer_run_active() && f0_mode()==START_LATCHED);
    /* Cut at EVERY write boundary, plus after magic is durable but before RAM
     * publication/readback. EEPROM reads do not alter the boot selection. */
    memcpy(image,fake_eeprom,sizeof image);
    for(cut=0;cut<=404;cut++) {
        fake_reset(); memcpy(fake_eeprom,image,sizeof image); f0_init(); loop(800);
        CHECK(app_commit_settings(&candidate)==RES_OK); writes=model_write_count();
        for(steps=0;steps<4000 && model_write_count()-writes<(cut>403?403:cut);steps++) loop(1);
        CHECK(steps<4000);
        if(cut==404) fake_advance(4);
        model_power_cut();
        CHECK(set_unpack(fake_eeprom+0x40,24,24,&old)==RES_OK);
        if(set_unpack(fake_eeprom+0x340,24,24,&newer)==RES_OK) {
            CHECK(newer.ch[0].trip_dC==1100 && newer.ch[0].alarm_dC==850); ++new_seen;
        }
        f0_init(); loop(800); CHECK(f0_mode()==START_LATCHED);
        CHECK(app_settings()->ch[0].trip_dC==1000 || app_settings()->ch[0].trip_dC==1100);
        CHECK((app_settings()->ch[0].trip_dC==1000 && app_settings()->ch[0].alarm_dC==800) ||
              (app_settings()->ch[0].trip_dC==1100 && app_settings()->ch[0].alarm_dC==850));
        if(cut%100==0) { printf("power-cut boundary %u/404 PASS\n",cut); fflush(stdout); }
    }
    CHECK(new_seen>0); printf("commit power cuts: 405 boundaries PASS (old and new observed)\n");
}
static unsigned events(event_type_t type) {
    events_t ring; event_t e; unsigned count=0,i;
    memcpy(&ring,fake_eeprom+0x840,sizeof ring);
    for(i=0;i<EVENT_SLOTS;i++) if(ev_unpack(ring.slot[i],&e)==RES_OK && e.type==type) ++count;
    return count;
}
static void lifecycle(void) {
    uint32_t feeds,start; settings_t candidate; unsigned i;
    running(); feeds=fake_feeds; start=tick_ms();
    for(i=0;i<8;i++) CHECK(!flow_check((uint8_t)(255u^(1u<<i)),255,scan_progress_ms()));
    CHECK(fake_feeds==feeds);
    fake_advance(250); CHECK(model_watchdog_reset()); CHECK(!timer_run_active());
    CHECK(tick_ms()-start<=251); f0_init(); loop(3000);
    CHECK(f0_mode()==START_LATCHED); CHECK(!timer_run_active());
    CHECK(events(EV_POWER_UP)==2); CHECK(ee_owner_cycles()==2);
    loop(1000); CHECK(events(EV_POWER_UP)==2);
    printf("S06 hung-loop watchdog: 250 ms; reset -> START_LATCHED\n");
    running(); candidate=*app_settings(); memcpy(candidate.ch[0].name,"ENGINE",6);
    CHECK(app_commit_settings(&candidate)==RES_OK); loop(2500);
    CHECK(f0_mode()==RUN && timer_run_active()); CHECK(memcmp(app_settings()->ch[0].name,"ENGINE",6)==0);
    CHECK(events(EV_NAME_CHANGED)==1); loop(1000); CHECK(events(EV_NAME_CHANGED)==1);
    candidate=*app_settings(); candidate.ch[0].trip_dC=1100;
    model_eeprom_fail(true); CHECK(app_commit_settings(&candidate)==RES_OK); loop(100);
    CHECK(!timer_run_active()); CHECK(app_settings()->ch[0].trip_dC==1000);
    CHECK(fault_latched_at(app_faults(),FC_G02_SAVE_FAIL_PROT,0));
    model_eeprom_fail(false); CHECK(app_commit_settings(&candidate)==RES_OK); loop(2500);
    CHECK(app_settings()->ch[0].trip_dC==1100); CHECK(!fault_active(app_faults(),FC_G02_SAVE_FAIL_PROT));
    fake_reset(); fixture(); fake_eeprom[0x640]=0; f0_init(); loop(3000);
    CHECK(f0_mode()==CONFIG_LOCK && !timer_run_active()); ack(); CHECK(f0_mode()==CONFIG_LOCK);
    fake_reset(); fixture(); fake_pin(board()->keys[2],false); f0_init(); loop(3000);
    CHECK(f0_mode()==SERVICE && !timer_run_active()); fake_pin(board()->keys[2],true);
    f0_init(); loop(3000); CHECK(f0_mode()==START_LATCHED && !timer_run_active());
    /* A held key cannot acknowledge a later trip, even after cooling. */
    running(); fake_pin(board()->keys[3],false); loop(100); temperature(1100); loop(750);
    temperature(250); loop(1500); CHECK(f0_mode()==TRIPPED); ack(); CHECK(f0_mode()==RUN);
    /* Both feedback channels reach the immediate fault path. */
    running();
    for(i=0;i<200;i++) { fake_pin(board()->alarm_sense,true); loop(1); }
    CHECK(f0_mode()==TRIPPED && fault_latched_at(app_faults(),FC_G07_ALARM_FEEDBACK,0));
}
static void write_records(void) {
    uint8_t bytes[SETTINGS_SLOT_SIZE];
    CHECK(set_pack(&cfg,bytes)==RES_OK); memcpy(fake_eeprom+0x40,bytes,SETTINGS_SLOT_SIZE);
    CHECK(cal_pack(&cal,bytes)==RES_OK); memcpy(fake_eeprom+0x640,bytes,CAL_SLOT_SIZE);
}
static void configurations(void) {
    settings_t candidate; calibration_t saved; unsigned ch,steps; uint8_t target;
    fake_reset(); fixture();
    for(ch=1;ch<24;ch++) { cfg.ch[ch]=cfg.ch[0]; cal.baseline_nV[ch]=3200000; cal.tag[ch]=1; }
    write_records(); f0_init(); loop(3000); CHECK(f0_mode()==START_LATCHED);
    ack(); loop(750); CHECK(f0_mode()==RUN && timer_run_active());
    /* C03 physical input 2n or 2n+1 belongs to channel n, not pin number. */
    fake_ad_code(0,13,0x800000);
    for(steps=0;steps<900 && f0_mode()==RUN;steps++) loop(1);
    CHECK(f0_mode()==TRIPPED); target=(uint8_t)((scan_current()->scan_no%16)/2);
    CHECK(fault_at(app_faults(),FC_C03_COMMON_MODE,target));
    CHECK(app_protection()->first.channel==target+1);
    fake_reset(); fixture(); cfg.ch[0].mode=CH_MODE_ALARM_ONLY; write_records(); f0_init(); loop(3000);
    ack(); loop(750); CHECK(timer_run_active()); temperature(1100); loop(750);
    CHECK(f0_mode()==RUN && timer_run_active() && app_output()->alarm_active);
    CHECK((fake_port(PORT_C)&0x40)==0);
    /* Epoch wrap must persist cleared calibration before epoch-zero settings. */
    fake_reset(); fixture(); cfg.ch[0].type_epoch=63; cal.tag[0]=253; write_records(); f0_init(); loop(3000);
    candidate=*app_settings(); CHECK(set_change_type(&candidate.ch[0],CH_TYPE_J)==RES_OK);
    candidate.ch[0].alarm_dC=800; candidate.ch[0].trip_dC=1000; candidate.ch[0].probe_limit_dC=12000;
    CHECK(app_commit_settings(&candidate)==RES_OK); loop(4500);
    CHECK(app_settings()->ch[0].type==CH_TYPE_J && app_settings()->ch[0].type_epoch==0);
    CHECK(f0_mode()==CONFIG_LOCK && !timer_run_active());
    CHECK(cal_unpack(fake_eeprom+0x740,3,&saved)==RES_OK);
    CHECK(saved.baseline_nV[0]==CAL_MISSING && saved.tag[0]==0);
    model_power_cut(); f0_init(); loop(3000); CHECK(f0_mode()==CONFIG_LOCK);
}
static void service_key(bool escape) {
    if(escape) { fake_pin(board()->keys[0],false); fake_pin(board()->keys[1],false); }
    else fake_pin(board()->keys[2],false);
    loop(30);
    fake_pin(board()->keys[0],true); fake_pin(board()->keys[1],true); fake_pin(board()->keys[2],true); loop(220);
}
static void service_owner(void) {
    settings_t candidate; calibration_t saved; unsigned step;
    fake_reset(); fixture(); fake_pin(board()->keys[2],false); f0_init(); loop(3000);
    CHECK(f0_mode()==SERVICE); fake_pin(board()->keys[2],true); loop(20);
    candidate=*app_settings(); memcpy(candidate.ch[0].name,"BENCH ",6);
    CHECK(app_commit_settings(&candidate)==RES_OK); loop(9000);
    CHECK(memcmp(app_settings()->ch[0].name,"BENCH ",6)==0);
    CHECK(svc_active_step()==1);
    for(step=1;step<=5;step++) { service_key(true); CHECK(svc_active_step()==step+1); }
    service_key(false); loop(15000); CHECK(svc_active_step()==7);
    service_key(false); service_key(false); loop(50000);
    CHECK(svc_finished()); CHECK(!timer_run_active()); CHECK(events(EV_CALIBRATION)==2);
    CHECK(strstr(fake_uart_log,"EVENTS_LOST ")!=NULL);
    CHECK(cal_unpack(fake_eeprom+0x640,3,&saved)==RES_OK);
    CHECK(saved.baseline_nV[0]!=CAL_MISSING && saved.tag[0]==1);
    CHECK(saved.baseline_nV[1]==CAL_MISSING && saved.tag[1]==0);
    model_power_cut(); f0_init(); loop(3000); CHECK(f0_mode()==START_LATCHED && !timer_run_active());
    fake_pin(board()->keys[2],false); model_power_cut(); f0_init(); loop(3000);
    CHECK(f0_mode()==SERVICE);
    timer_run_start(1000); /* inject corruption during the service output bypass */
    ((prot_state_t *)app_protection())->mode_inv^=1;
    loop(1); CHECK(!timer_run_active() && f0_mode()==TRIPPED);
    CHECK(fault_active(app_faults(),FC_G04_INTERNAL));
}
static bool first_new_event(uint16_t previous,event_t *first) {
    event_t e; uint16_t closest=UINT16_MAX; unsigned slot;
    for(slot=0;slot<EVENT_SLOTS;slot++) if(ev_unpack(fake_eeprom+0x840+16*slot,&e)==RES_OK) {
        uint16_t delta=(uint16_t)(e.sequence-previous);
        if(delta && delta<0x8000u && delta<closest) { *first=e; closest=delta; }
    }
    return closest!=UINT16_MAX;
}
static void island_burst(void) {
    unsigned ch,step; first_out_t first; events_t ring; event_t last,stored;
    fake_reset(); fixture();
    for(ch=1;ch<24;ch++) { cfg.ch[ch]=cfg.ch[0]; cal.baseline_nV[ch]=3200000; cal.tag[ch]=1; }
    write_records(); f0_init(); loop(3000); ack(); loop(750);
    CHECK(f0_mode()==RUN && timer_run_active());
    memcpy(&ring,fake_eeprom+0x840,sizeof ring); CHECK(ev_get(&ring,0,&last)==RES_OK);
    for(ch=0;ch<3;ch++) fake_ad_crc((uint8_t)ch,255);
    for(step=0;step<900 && !fault_active(app_faults(),FC_G14_ISLAND_LOST);step++) loop(1);
    CHECK(step<900 && f0_mode()==TRIPPED); first=app_protection()->first;
    /* Replay the simultaneous per-channel detector fan-out at the registry
     * seam, alongside the real ADC transport/island failure. This makes the
     * notification burst independent of which scan slot lost power. */
    for(ch=0;ch<24;ch++) (void)fault_raise((fault_registry_t *)app_faults(),FC_C02_RANGE,(uint8_t)ch);
    loop(1);
    CHECK(fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO)); CHECK(ee_owner_events_lost()>0);
    CHECK(!fault_active(app_faults(),FC_G04_INTERNAL));
    for(ch=0;ch<3;ch++) fake_ad_crc((uint8_t)ch,0);
    for(step=0;step<200 && !first_new_event(last.sequence,&stored);step++) loop(1);
    CHECK(step<200 && stored.type==EV_TRIP);
    CHECK(stored.code==first.code && stored.channel==first.channel);
    CHECK(stored.value_dC==first.value_dC && stored.threshold_dC==first.threshold_dC);
    CHECK(stored.uptime_s==first.uptime_s);
    CHECK(stored.unit==(first.code>=FC_B01_ADC_ID?(uint8_t)(first.unit+1):0));
    loop(3000); CHECK(scan_last()->scan_validated);
    CHECK(ee_owner_events_drained() && fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO));
    ack();
    CHECK(f0_mode()==RUN); CHECK(!fault_active(app_faults(),FC_G04_INTERNAL));
    CHECK(!fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO));
    CHECK(!fault_latched_at(app_faults(),FC_G13_SAVE_FAIL_INFO,0));
    loop(750); CHECK(timer_run_active());
    CHECK(first.valid);
    printf("island burst: recovered without reset; events lost=%lu; first TRIP=%u\n",
           (unsigned long)ee_owner_events_lost(),(unsigned)stored.code);
}
static void overflow_ack(void) {
    event_t e; uint32_t lost; unsigned i; settings_t candidate;
    running(); CHECK(ee_owner_events_drained());
    memset(&e,0,sizeof e); e.type=EV_NAME_CHANGED;
    for(i=0;i<32;i++) { e.value_dC=(temp_dC_t)i; CHECK(ee_owner_log(&e)); }
    e.value_dC=32000; CHECK(!ee_owner_log(&e)); loop(1);
    CHECK(ee_owner_events_lost()>0 && fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO));
    ack(); CHECK(f0_mode()==RUN); CHECK(fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO));
    loop(2400); CHECK(ee_owner_events_drained());
    CHECK(fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO)); /* draining alone cannot clear it */
    lost=ee_owner_events_lost(); ack(); CHECK(!fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO));
    CHECK(!fault_latched_at(app_faults(),FC_G13_SAVE_FAIL_INFO,0));
    CHECK(ee_owner_events_lost()==lost && f0_mode()==RUN && timer_run_active());
    for(i=0;i<EVENT_SLOTS;i++) if(ev_unpack(fake_eeprom+0x840+16*i,&e)==RES_OK) CHECK(e.value_dC!=32000);
    /* The event-loss ACK must not erase a separate names-save G13 source. */
    running(); candidate=*app_settings(); memcpy(candidate.ch[0].name,"RETRY ",6);
    model_eeprom_fail(true); CHECK(app_commit_settings(&candidate)==RES_OK); loop(20);
    CHECK(fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO)); model_eeprom_fail(false);
    memset(&e,0,sizeof e); e.type=EV_NAME_CHANGED;
    for(i=0;i<33;i++) (void)ee_owner_log(&e);
    loop(2600); CHECK(ee_owner_events_drained() && ee_owner_events_lost()>0);
    ack(); CHECK(f0_mode()==RUN && fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO));
    CHECK(app_commit_settings(&candidate)==RES_OK); loop(2500); ack();
    CHECK(!fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO));
    CHECK(!fault_latched_at(app_faults(),FC_G13_SAVE_FAIL_INFO,0));
}
static void first_out_last_slot(void) {
    event_t e; first_out_t first; unsigned i,trips=0;
    running(); CHECK(ee_owner_events_drained());
    memset(&e,0,sizeof e); e.type=EV_NAME_CHANGED;
    for(i=0;i<31;i++) CHECK(ee_owner_log(&e));
    (void)fault_raise((fault_registry_t *)app_faults(),FC_G08_ENGREF_LOST,0); loop(1);
    CHECK(f0_mode()==TRIPPED); first=app_protection()->first;
    CHECK(ee_owner_events_lost()>0 && !fault_active(app_faults(),FC_G04_INTERNAL));
    loop(2500); CHECK(ee_owner_events_drained());
    for(i=0;i<EVENT_SLOTS;i++) if(ev_unpack(fake_eeprom+0x840+16*i,&e)==RES_OK && e.type==EV_TRIP) {
        CHECK(e.code==first.code && e.uptime_s==first.uptime_s); ++trips;
    }
    CHECK(trips==1); /* the final free slot went to first-out, ahead of FAULT */
    ack(); CHECK(f0_mode()==RUN && !fault_active(app_faults(),FC_G13_SAVE_FAIL_INFO));
}
static void service_lost_report(void) {
    event_t e; unsigned i;
    fake_reset(); fixture(); fake_pin(board()->keys[2],false); f0_init(); loop(3000);
    CHECK(f0_mode()==SERVICE && ee_owner_events_drained());
    memset(&e,0,sizeof e); e.type=EV_NAME_CHANGED;
    for(i=0;i<32;i++) CHECK(ee_owner_log(&e));
    CHECK(!ee_owner_log(&e)); loop(9000);
    CHECK(ee_owner_events_lost()==1);
    CHECK(strstr(fake_uart_log,"P17 EVENTS_LOST 1 OK")!=NULL);
}
void test_main(void) {
    model_enable();
    island_burst(); overflow_ack(); first_out_last_slot(); service_lost_report();
    safety(); injected(); lifecycle(); configurations(); service_owner(); commits();
    printf("host modeled loop worst: %lu us (I/O timing; AVR CPU WCET requires bench)\n",(unsigned long)worst_us);
    printf("integration: %u checks PASS; S01-S06, S09-S12, S14, commit power cuts\n",checks);
}
