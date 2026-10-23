#include "app/app.h"
#include "app/service.h"
#include "services/scan.h"
#include "mcal/timer.h"
#include "mcal/gpio.h"
#include "fake_hw.h"
#include "model.h"
#include "scan_jitter.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)) { printf("gap FAIL %u: %s\n",(unsigned)__LINE__,#x); exit(1); } } while(0)
static void step(uint8_t ms) {
    uint32_t used;
    model_loop_begin(); f0_task(); used=model_loop_us();
    CHECK(used<=20000u && !model_watchdog_reset());
    if(used<(uint32_t)ms*1000u) model_cpu_us((uint16_t)((uint32_t)ms*1000u-used));
}
static void setup(void) {
    settings_t s; calibration_t c; uint8_t raw[SETTINGS_SLOT_SIZE]; unsigned i;
    fake_reset(); memset(&s,0,sizeof s); memset(&c,0,sizeof c);
    s.board_type=s.channel_count=24; s.address=1; c.bank_count=3;
    for(i=0;i<24;i++) {
        memcpy(s.ch[i].name,"GAP   ",6); s.ch[i].type=CH_TYPE_K;
        s.ch[i].band_C=2; s.ch[i].alarm_dC=800; s.ch[i].trip_dC=1000;
        s.ch[i].probe_limit_dC=2000; c.baseline_nV[i]=3200000; c.tag[i]=1;
    }
    CHECK(set_pack(&s,raw)==RES_OK); memcpy(fake_eeprom+0x40,raw,sizeof raw);
    CHECK(cal_pack(&c,raw)==RES_OK); memcpy(fake_eeprom+0x640,raw,CAL_SLOT_SIZE);
    f0_init(); for(i=0;i<1500;i++) step(5);
    fake_pin(board()->keys[3],false); for(i=0;i<20;i++) step(5);
    fake_pin(board()->keys[3],true); for(i=0;i<300;i++) step(5);
    CHECK(f0_mode()==RUN && timer_run_active());
    for(i=0;i<3;i++) fake_ad_ready((uint8_t)i,49);
}
static void ref_retry(bool restore) {
    uint32_t at,last,low_at=0; unsigned i,n=0; bool pulse=false;
    setup();scan_test_ref_due();fake_pin(board()->refok,true);
    for(i=0;i<150 && f0_mode()==RUN;i++) step(20);
    CHECK(i<150 && f0_mode()==TRIPPED && !timer_run_active());
    CHECK(app_protection()->first.code==FC_G08_ENGREF_LOST);
    at=tick_ms();last=scan_last()->scan_no;
    while(tick_ms()-at<5000u) {
        step(20);CHECK(!timer_run_active() && !(fake_port(PORT_A)&8u));
        if(scan_last()->scan_no!=last) { last=scan_last()->scan_no;++n;CHECK(!scan_last()->scan_validated); }
    }
    CHECK(n>=4 && !scan_diagnostics()->ref_test_ok);
    if(!restore) return;
    fake_pin(board()->refok,false);at=tick_ms();
    for(i=0;i<150;i++) {
        step(20);CHECK(f0_mode()==TRIPPED && !timer_run_active());
        if(fake_port(PORT_A)&8u) pulse=true;
        else if(pulse && !low_at) low_at=tick_ms();
        if(scan_last()->scan_no!=last) {
            last=scan_last()->scan_no;
            if(scan_diagnostics()->ref_test_ok) {
                CHECK(scan_last()->scan_validated && pulse && low_at && tick_ms()-low_at>=20u);
                break; /* The first completion after the successful test must validate. */
            }
            CHECK(!scan_last()->scan_validated);
        }
    }
    CHECK(i<150 && tick_ms()-at<3000u);
    CHECK(!fault_active(app_faults(),FC_G08_ENGREF_LOST));
    CHECK(fault_latched_at(app_faults(),FC_G08_ENGREF_LOST,0));
    step(20);fake_pin(board()->keys[3],false);for(i=0;i<6;i++) step(20);
    fake_pin(board()->keys[3],true);for(i=0;i<70;i++) step(20);
    CHECK(app_ack_reason()==ACK_NONE && f0_mode()==RUN && timer_run_active());
    printf("F8 REF retry: restored after 5 s; validated automatically, fresh key ACK restores RUN\n");
}
void test_gap(void) {
    uint8_t p;
    for(p=0;p<4;p++) {
        uint16_t index=0,worst=0; uint32_t seed=0x24F70001UL,last,at,low_at=0; unsigned i,n=0,ref=0;
        bool was_high=false,recovering=false;
        setup(); last=scan_last()->scan_no; at=scan_last()->completed_ms;
        scan_test_ref_due();
        for(i=0;i<8000 && n<24;i++) {
            uint8_t b; step(scan_jitter_next(p,&index,&seed));
            CHECK(f0_mode()==RUN && timer_run_active());
            bool high=(fake_port(PORT_A)&(1u<<3))!=0;
            if(high) {
                ++ref;
                for(b=0;b<3;b++) {
                    uint8_t channel; bool active=false;
                    for(channel=0;channel<15;channel++) if(fake_ad_get(b,(uint8_t)(9+channel))&0x8000u) {
                        CHECK(channel>=10 && channel<=12); active=true;
                    }
                    CHECK(active);
                }
            }
            if(was_high && !high) { low_at=tick_ms();recovering=true; }
            if(recovering) for(b=0;b<3;b++) if(fake_ad_get(b,22)&0x8000u) {
                CHECK(tick_ms()-low_at>=20u);recovering=false;
            }
            was_high=high;
            if(scan_last()->scan_no==last) continue;
            {
                uint32_t gap=scan_last()->completed_ms-at;
                CHECK(scan_last()->scan_validated && gap<=1100u);
                CHECK(scan_diagnostics()->duration_ms==gap);
                if(gap>worst) worst=(uint16_t)gap;
            }
            at=scan_last()->completed_ms; last=scan_last()->scan_no; ++n;
        }
        CHECK(n==24 && ref && scan_diagnostics()->ref_test_ok);
        CHECK(!fault_latched_at(app_faults(),FC_G05_SCAN_DEADLINE,0));
        printf("F7 host jitter %u: gap %u ms; 24 validated, REF exercised, RUN uninterrupted\n",p,worst);
    }
    ref_retry(true);ref_retry(false);
    printf("Scan gap/REF retry: %u checks PASS\n",checks);
}
