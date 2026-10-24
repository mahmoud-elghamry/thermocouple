/* Continuous 20-ms cadence: no skipped firmware passes or rebased timestamps. */
#include "app/app.h"
#include "app/app_view.h"
#include "app/ee_owner.h"
#include "app/service.h"
#include "app/stack_monitor.h"
#include "app/stack_budget.h"
#include "app/ui.h"
#include "app/modbus.h"
#include "app/timing.h"
#include "services/scan.h"
#include "services/tc_math.h"
#include "drivers/keys.h"
#include "drivers/relays.h"
#include "mcal/timer.h"
#include "mcal/gpio.h"
#include "fake_hw.h"
#include "model.h"
#include "scan_jitter.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks;
static uint64_t elapsed_us,passes;
static uint64_t next_bounds;
static uint32_t random_state=0x24F60001u,last_tick,wraps,worst_us,cuts,saves,refusals,accepted,ring_wraps;
static uint16_t last_event;
static bool have_event,flood;
static bool uptime_wrapped;
static uint8_t hot_channel=255;
static uint32_t hot_code,hot_scan;
static uint8_t jitter_pattern=255;
static uint16_t jitter_index;
static uint32_t jitter_seed;
#define CHECK(x) do { ++checks; if(!(x)) { printf("soak FAIL %u: %s tick=%lu mode=%u ack=%u cause=%u channel=%u\n",(unsigned)__LINE__,#x,(unsigned long)tick_ms(),f0_mode(),app_ack_reason(),app_protection()->first.code,app_output()->refusal_channel); exit(1); } } while(0)
static void clock_test(void) {
    unsigned fast; uint32_t reference[12];
    for(fast=0;fast<2;fast++) {
        unsigned i; fake_reset(); model_enable(); model_fast_ticks(fast!=0); timer_init(); keys_init();
        timer_run_start(120);
        for(i=0;i<12;i++) {
            uint32_t value;
            fake_pin(board()->keys[3],i>=3 && i<8); fake_advance(i==11?1200u:17u);
            value=(tick_ms()<<16)|(timer_run_remaining()<<4)|keys_held();
            if(fast) CHECK(value==reference[i]); else reference[i]=value;
        }
        CHECK(timer_run_expired() && model_watchdog_reset());
        timer_init(); timer_run_start(1200); fake_advance(2000);
        CHECK(model_watchdog_reset() && !timer_run_expired() && !timer_run_active());
    }
    fake_reset(); model_enable(); model_fast_ticks(true); timer_init();
    fake_advance(4300000UL); /* beyond the microsecond clock's first wrap */
    CHECK(tick_ms()==4300000UL);
    gpio_init(); relay_alarm(true); CHECK(!gpio_read(board()->alarm_sense));
    model_power_cut(); CHECK(gpio_read(board()->alarm_sense));
    printf("Soak model clock: %lu checks PASS\n",checks);
}
static uint32_t random_next(void) {
    random_state^=random_state<<13; random_state^=random_state>>17; random_state^=random_state<<5;
    return random_state;
}
static void step(void) {
    uint32_t duration,now,target; unsigned i;
    if(hot_channel<MAX_CHANNELS && scan_current()->scan_no!=hot_scan) {
        hot_scan=scan_current()->scan_no;
        fake_ad_code(hot_channel/8,14,(uint32_t)(hot_channel%8u)==hot_scan%8u?hot_code+343597u:0x853E2D);
    }
    if(flood) for(i=0;i<16;i++) fake_uart_receive((uint8_t)random_next(),0);
    model_loop_begin(); f0_task(); duration=model_loop_us();
    CHECK(duration<=APP_LOOP_BUDGET_MS*1000u && !model_watchdog_reset());
    if(duration>worst_us) worst_us=duration;
    elapsed_us+=duration;
    target=jitter_pattern<4?(uint32_t)scan_jitter_next(jitter_pattern,&jitter_index,&jitter_seed)*1000u:20000u;
    if(duration<target) { model_cpu_us((uint16_t)(target-duration)); elapsed_us+=target-duration; }
    now=tick_ms(); if(now<last_tick) { ++wraps; uptime_wrapped=true; } last_tick=now; ++passes;
    if(elapsed_us>=next_bounds) {
        const fault_registry_t *f=app_faults();
        CHECK(ee_owner_invariants() && app_stack_highwater()<APP_STACK_BYTES && fake_uart_rx_count()<=64);
        if(f) CHECK(!f->internal && !fault_active(f,FC_G04_INTERNAL));
        next_bounds=elapsed_us+60000000u;
    }
}
static void run_ms(uint32_t duration) {
    uint64_t end=elapsed_us+(uint64_t)duration*1000u;
    while(elapsed_us<end) step();
}
static void ack(void) {
    fake_pin(board()->keys[3],true); run_ms(40);
    fake_pin(board()->keys[3],false); run_ms(100);
    fake_pin(board()->keys[3],true); run_ms(40);
    if(app_ack_reason()==ACK_NONE) ++accepted;
}
static void key(key_t k) { CHECK(ui_key(k)); run_ms(60); }
static void fixture(void) {
    settings_t s; calibration_t c; uint8_t raw[SETTINGS_SLOT_SIZE]; unsigned ch;
    memset(&s,0,sizeof s); memset(&c,0,sizeof c);
    s.board_type=24; s.channel_count=24; s.address=1; s.baud=1; c.bank_count=3;
    /* Explicit test inputs: all fitted, 80/100 C limits and 200 C probes. */
    for(ch=0;ch<MAX_CHANNELS;ch++) {
        memcpy(s.ch[ch].name,"SOAK  ",6); s.ch[ch].band_C=2; s.ch[ch].type=CH_TYPE_K;
        s.ch[ch].alarm_dC=800; s.ch[ch].trip_dC=1000; s.ch[ch].probe_limit_dC=2000;
        c.baseline_nV[ch]=3200000; c.tag[ch]=1;
    }
    CHECK(set_pack(&s,raw)==RES_OK); memcpy(fake_eeprom+0x40,raw,sizeof raw);
    CHECK(cal_pack(&c,raw)==RES_OK); memcpy(fake_eeprom+0x640,raw,CAL_SLOT_SIZE);
}
static void boot(void) {
    unsigned i;
    fake_pin(board()->keys[3],true); fake_pin(board()->refok,false);
    f0_init(); last_tick=tick_ms(); have_event=false; uptime_wrapped=false;
    for(i=0;i<1500;i++) {
        step();
        if(i>300 && f0_mode()==START_LATCHED && scan_last()->scan_no>=2 && scan_last()->scan_validated) break;
    }
    CHECK(i<1500 && f0_mode()==START_LATCHED && scan_last()->scan_validated);
    ack(); run_ms(1400);
    CHECK(f0_mode()==RUN && timer_run_active());
}
static void temperature(uint8_t ch,bool hot) {
    emf_nV_t e,cj; uint32_t code=0x800000;
    if(hot) {
        CHECK(tc_dC_to_emf(CH_TYPE_K,1437,&e)==RES_OK && tc_dC_to_emf(CH_TYPE_K,250,&cj)==RES_OK);
        code=(uint32_t)(0x800000LL+(int64_t)(e-cj)*32*8388608/2500000000LL);
    }
    fake_ad_code(ch/8,ch%8,code);
    hot_channel=hot?ch:255; hot_code=code; hot_scan=scan_current()->scan_no;
    fake_ad_code(ch/8,14,hot && (uint32_t)(ch%8u)==hot_scan%8u?code+343597u:0x853E2D);
}
static void jitter_test(void) {
    uint8_t p,b;
    for(b=0;b<3;b++) fake_ad_ready(b,49);
    for(p=0;p<4;p++) {
        unsigned n=0,i,ref=0; uint16_t worst=0; uint32_t last=scan_last()->scan_no,at=scan_last()->completed_ms;
        jitter_pattern=p;jitter_index=0;jitter_seed=0x24F70001UL;scan_test_ref_due();
        for(i=0;i<8000 && n<24;i++) {
            step();CHECK(f0_mode()==RUN && timer_run_active());
            if(fake_port(PORT_A)&8u) ++ref;
            if(scan_last()->scan_no==last) continue;
            {
                uint32_t gap=scan_last()->completed_ms-at;
                CHECK(scan_last()->scan_validated && gap<=1100u && gap==scan_diagnostics()->duration_ms);
                if(gap>worst) worst=(uint16_t)gap;
            }
            last=scan_last()->scan_no;at=scan_last()->completed_ms;++n;
        }
        CHECK(n==24 && ref && scan_diagnostics()->ref_test_ok);
        CHECK(!fault_latched_at(app_faults(),FC_G05_SCAN_DEADLINE,0));
        printf("Soak jitter %u: worst gap %u ms; 24 validated, REF, RUN uninterrupted\n",p,worst);
    }
    jitter_pattern=255;for(b=0;b<3;b++) fake_ad_ready(b,43);
}
static void invariants(void) {
    event_t e; uint8_t n,age; const fault_registry_t *f=app_faults();
    CHECK(ee_owner_invariants() && !f->internal && !fault_active(f,FC_G04_INTERNAL));
    CHECK(app_stack_highwater()<APP_STACK_BYTES && fake_uart_rx_count()<=64);
    CHECK(ui_test_state()->channel<MAX_CHANNELS && ui_test_state()->screen<=UI_RECOVER);
    CHECK(set_validate(app_settings())==RES_OK && scan_last()->scan_validated);
    CHECK(scan_diagnostics()->duration_ms<APP_SCAN_DEADLINE_MS);
    if(f0_mode()!=RUN) CHECK(!timer_run_active());
    if(ee_owner_events_drained()) {
        for(age=0;age<EVENT_SLOTS;age++) {
            res_t r=ee_owner_history(age,&n,&e);
            CHECK(n<=EVENT_SLOTS && (r==RES_OK || r==RES_ERR_RANGE));
            if(r==RES_OK) CHECK(e.channel<=MAX_CHANNELS && e.uptime_s<=0xFFFFFFUL);
            if(age==0 && r==RES_OK) {
                if(have_event && e.sequence<last_event && (uint16_t)(e.sequence-last_event)<0x8000u) ++ring_wraps;
                last_event=e.sequence; have_event=true;
            }
        }
    }
}
static void ack_when_clear(void) {
    {
        unsigned i;
        /* A real input step between the TC/burnout pair can also latch C01/C06;
         * their next scheduled owning-channel check is once in eight scans. */
        for(i=0;i<1000;i++) {
            if(!fault_active(app_faults(),FC_C01_OPEN) && !fault_active(app_faults(),FC_C06_SHORTED) &&
               scan_last()->scan_validated && tick_ms()-scan_last()->completed_ms<1000u) {
                ack(); if(f0_mode()==RUN) break;
            }
            run_ms(200);
        }
        CHECK(i<1000);
    }
    run_ms(1200); CHECK(f0_mode()==RUN && timer_run_active());
}
static void trip_episode(bool fault) {
    uint8_t ch=(uint8_t)(random_next()%24u);
    if(fault) fake_pin(board()->refok,true); else temperature(ch,true);
    /* Past the old window: its G05 is a new fault and refuses an ACK held at that moment (R1). */
    run_ms(APP_RUN_WINDOW_MS+100u); CHECK(f0_mode()==TRIPPED && !timer_run_active());
    if(uptime_wrapped) CHECK(app_protection()->first.uptime_s>=UINT32_MAX/1000u);
    ack();
    /* R2 precedes R3 when an island fault has invalidated the completed scan. */
    CHECK(fault?(app_ack_reason()==ACK_R2_SCAN || app_ack_reason()==ACK_R3_FAULT):app_ack_reason()==ACK_R4_CHANNEL); ++refusals;
    if(fault) fake_pin(board()->refok,false); else temperature(ch,false);
    run_ms(3000); ack_when_clear();
}
static void ui_save(bool protection,bool cut) {
    static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -/";
    settings_t before=*app_settings(),wanted; uint32_t writes; unsigned i;
    wanted=before; wanted.sequence++;
    if(protection) wanted.ch[0].trip_dC=(temp_dC_t)(before.ch[0].trip_dC+(before.ch[0].trip_dC>=1010?-10:10));
    else {
        const char *position=strchr(alphabet,before.ch[0].name[0]); CHECK(position!=NULL);
        wanted.ch[0].name[0]=position[1]?position[1]:alphabet[0];
    }
    key(KEY_ESC); key(KEY_SET_LONG); for(i=0;i<4;i++) key(KEY_SET); /* saved PIN 0000 */
    CHECK(ui_current_screen()==UI_SETUP); key(KEY_SET); key(KEY_SET);
    for(i=0;i<(protection?4u:2u);i++) key(KEY_DOWN);
    key(KEY_SET); key(protection && before.ch[0].trip_dC>=1010?KEY_DOWN:KEY_UP); key(KEY_SET);
    if(!protection) for(i=0;i<5;i++) key(KEY_SET);
    key(KEY_ESC); key(KEY_ESC); CHECK(ui_current_screen()==UI_CONFIRM);
    key(KEY_SET); writes=model_settings_write_count();
    if(cut) {
        uint32_t at=random_next()%405u;
        for(i=0;i<3000 && model_settings_write_count()-writes<at;i++) step();
        /* Arbitrary point inside the outstanding EEPROM byte, not just boundaries. */
        model_cpu_us((uint16_t)(random_next()%3400u));
        model_power_cut(); ++cuts; fake_ad_reset(); fake_tmp_reset(); boot();
        CHECK(!memcmp(app_settings(),&before,sizeof before) || !memcmp(app_settings(),&wanted,sizeof wanted));
    } else {
        for(i=0;i<2000 && app_settings()->sequence==before.sequence;i++) step();
        CHECK(i<2000 && app_settings()->sequence==before.sequence+1u); ++saves;
        CHECK(!memcmp(app_settings(),&wanted,sizeof wanted));
        CHECK(f0_mode()==(protection?START_LATCHED:RUN));
        if(protection) {
            for(i=0;i<1500;i++) {
                if(scan_last()->scan_no>=2 && scan_last()->scan_validated && scan_last()->settings_seq==app_settings()->sequence) break;
                step();
            }
            CHECK(i<1500); ack(); run_ms(1200);
        }
        CHECK(timer_run_active());
    }
}
static void modbus_read(void) {
    uint8_t q[8]={1,4,0,0,0,20,0,0}; uint16_t crc=mb_crc16(q,6),n=0; unsigned i,attempt;
    q[6]=(uint8_t)crc; q[7]=(uint8_t)(crc>>8);
    /* A scan publication cancels a partially built snapshot; master retries. */
    for(attempt=0;attempt<10 && n==0;attempt++) {
        fake_uart_clear(); run_ms(60);
        for(i=0;i<8;i++) { fake_uart_receive(q[i],0); model_cpu_us(600); elapsed_us+=600; }
        run_ms(2000); n=fake_uart_tx_size();
    }
    CHECK(n==45 && mb_crc16((const uint8_t *)fake_uart_log,n)==0);
    CHECK((uint8_t)fake_uart_log[6]==24 && (uint8_t)fake_uart_log[8]==24);
}
static void uptime_field(void) {
    event_t e,out; uint8_t raw[16]; uint32_t t;
    memset(&e,0,sizeof e); e.type=EV_TRIP; e.code=FC_C10_OVER_TRIP; e.channel=24;
    for(t=0xFFFFFEUL;t<=0x1000001UL;t++) {
        e.uptime_s=t; CHECK(ev_pack(&e,raw)==RES_OK && ev_unpack(raw,&out)==RES_OK);
        CHECK(out.uptime_s==(t&0xFFFFFFUL) && out.channel==24 && out.code==FC_C10_OVER_TRIP);
    }
}
static void persisted_uptime_field(void) {
    uint32_t t; event_t e,out; uint8_t n; unsigned i;
    /* 05 section 7: u24 seconds wraps at 194 days, beyond a 60-day soak.
     * Inject those wire-boundary timestamps through the real EEPROM owner. */
    for(t=0xFFFFFEUL;t<=0x1000001UL;t++) {
        for(i=0;i<3000 && !ee_owner_events_drained();i++) step();
        CHECK(i<3000); memset(&e,0,sizeof e); e.type=EV_NAME_CHANGED; e.uptime_s=t;
        CHECK(ee_owner_log(&e));
        for(i=0;i<3000 && !ee_owner_events_drained();i++) step();
        CHECK(i<3000 && ee_owner_history(0,&n,&out)==RES_OK);
        CHECK(out.type==EV_NAME_CHANGED && out.uptime_s==(t&0xFFFFFFUL));
    }
}
int main(int argc,char **argv) {
    uint64_t end,next=0; uint32_t days,minutes,episodes=0,wrap_refusals=0; bool wrap_hot=false;
    bool wrap_test=argc>1 && !strcmp(argv[1],"--wrap-test");
    event_t e;
    if(argc>1 && !strcmp(argv[1],"--clock-test")) { clock_test(); return 0; }
    days=wrap_test?60:argc>1?(uint32_t)strtoul(argv[1],NULL,10):60;
    minutes=wrap_test?1:argc>2?(uint32_t)strtoul(argv[2],NULL,10):0;
    CHECK(days>0 && days<=60); end=minutes?(uint64_t)minutes*60000000u:(uint64_t)days*86400000000ULL;
    clock_test(); uptime_field(); fake_reset(); model_enable(); model_fast_ticks(true); fixture(); boot();
    if(!wrap_test) jitter_test();
    if(wrap_test) {
        model_power_cut(); model_boot_epoch(UINT32_MAX-20000u); boot(); next=60000000u;
    } else {
        unsigned minute;
        for(minute=0;minute<11;minute++) {
            run_ms(60000); CHECK(f0_mode()==RUN && timer_run_active()); invariants();
        }
    }
    while(elapsed_us<end) {
        if(!wrap_hot && tick_ms()>UINT32_MAX-2500u) {
            temperature(0,true); run_ms(1200); CHECK(f0_mode()==TRIPPED);
            wrap_hot=true; fake_pin(board()->keys[3],false);
        }
        if(wrap_hot && tick_ms()<1000u) {
            CHECK(!timer_run_active() && app_ack_reason()==ACK_R4_CHANNEL); ++wrap_refusals;
            fake_pin(board()->keys[3],true); temperature(0,false); run_ms(3000); ack_when_clear(); run_ms(1400);
            CHECK(timer_run_active()); wrap_hot=false;
            trip_episode(false);
        }
        if(elapsed_us>=next && !wrap_hot) {
            uint32_t choice=random_next()%8u; uint64_t day=elapsed_us/86400000000ULL;
            next=elapsed_us+60000000u; /* inspect every simulated minute */
            if(choice<2) trip_episode(choice!=0);
            else if(choice<4) ui_save(choice==3,false);
            else if(choice==4) modbus_read();
            else if(choice==5 && (day<3 || day>=57)) ui_save(false,true);
            else if(choice==6) { flood=true; trip_episode(false); flood=false; run_ms(300); }
            else {
                unsigned i; memset(&e,0,sizeof e); e.type=EV_NAME_CHANGED;
                for(i=0;i<40;i++) (void)ee_owner_log(&e);
                CHECK(ee_owner_events_lost()>0);
                if((day<3 || day>=57) && random_next()%8u==0) {
                    run_ms(random_next()%1000u); model_cpu_us((uint16_t)(random_next()%3400u));
                    model_power_cut(); ++cuts; fake_ad_reset(); fake_tmp_reset(); boot();
                } else { run_ms(14000); ack(); }
            }
            ++episodes; run_ms(1500); invariants();
            if(episodes%1440u==0) { printf("Soak progress: %lu minutes, wraps=%lu cuts=%lu\n",(unsigned long)(elapsed_us/60000000u),(unsigned long)wraps,(unsigned long)cuts); fflush(stdout); }
        } else step();
    }
    if(!minutes && days==60) { CHECK(wraps>0 && wrap_refusals>0 && cuts>0 && ring_wraps>0); }
    if(wrap_test) { CHECK(wraps==1 && wrap_refusals==1); }
    persisted_uptime_field();
    printf("Soak: %lu checks PASS; %llu passes, %llu simulated minutes; wraps=%lu wrap-ACK=%lu event-sequence-wraps=%lu cuts=%lu saves=%lu ACK accepted/refused=%lu/%lu; loop=%lu us; seed=24F60001\n",checks,(unsigned long long)passes,(unsigned long long)(elapsed_us/60000000u),(unsigned long)wraps,(unsigned long)wrap_refusals,(unsigned long)ring_wraps,(unsigned long)cuts,(unsigned long)saves,(unsigned long)accepted,(unsigned long)refusals,(unsigned long)worst_us);
    return 0;
}
