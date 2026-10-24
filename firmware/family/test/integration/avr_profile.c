/* AVR instruction simulator harness: real shell and drivers, register fakes.
 * No WDR instruction: the GNU simulator does not implement it. */
#include "app/app.h"
#include "app/stack_monitor.h"
#include "app/ee_owner.h"
#include "app/service.h"
#include "services/scan.h"
#include "services/tc_math.h"
#include "drivers/keys.h"
#include "app/acquisition_budget.h"
#include "drivers/lcd.h"
#include "app/ui.h"
#include "mcal/timer.h"
#include "mcal/flash_crc.h"
#include "fake_hw.h"
#include "scan_jitter.h"
#include <string.h>
/* A retained byte below __heap_start must survive stack painting. */
volatile uint8_t profile_retained __attribute__((used,externally_visible,section(".noinit")));
void profile_retained_seed(void) __attribute__((naked,used,section(".init1")));
void profile_retained_seed(void) {
    __asm__ volatile("ldi r24,0x6d\n\tsts profile_retained,r24":::"memory");
}
volatile uint16_t profile_pass;
volatile uint8_t profile_measuring,profile_task_kind;
volatile uint8_t profile_phase,profile_errors,profile_mixed,profile_rearm;
volatile uint32_t profile_delay,profile_elapsed_us;
volatile uint16_t profile_stack,profile_stack_capacity,profile_cadence_us,profile_failure;
volatile uint16_t profile_scan_ms[3];
volatile uint8_t profile_scan_count[3];
volatile uint16_t profile_gap_ms[4];
volatile uint8_t profile_gap_count[4],profile_ref_seen[4];
volatile uint8_t profile_ref_retry;
volatile uint16_t profile_ref_recovery_ms;
static uint8_t jitter_pattern=255;
static uint16_t jitter_index;
static uint32_t jitter_seed=0x24F70001UL;
uint8_t profile_eeprom_read(uint16_t a) {
    if(a>=0x40 && a<0x640) return fake_eeprom[(a-0x40)%768];
    if(a>=0x640 && a<0x840) return fake_eeprom[768+(a-0x640)%256];
    return 0xFF;
}
void profile_eeprom_write(uint16_t a,uint8_t v) {
    if(a>=0x40 && a<0x640) fake_eeprom[(a-0x40)%768]=v;
    if(a>=0x640 && a<0x840) fake_eeprom[768+(a-0x640)%256]=v;
}
void flash_crc_begin(void) { }
res_t flash_crc(void) { return RES_OK; }
uint16_t flash_crc_value(void) { return 0; }
__attribute__((noinline,noclone,used)) void profile_begin(void) { profile_measuring=1; __asm__ volatile("nop":::"memory"); }
__attribute__((noinline,noclone,used)) void profile_end(void) { profile_measuring=0; __asm__ volatile("nop":::"memory"); }
__attribute__((noinline,noclone,used)) void profile_task_begin(void) { __asm__ volatile("nop":::"memory"); }
__attribute__((noinline,noclone,used)) void profile_task_end(void) { __asm__ volatile("nop":::"memory"); }
__attribute__((noinline,noclone,used)) void profile_done(void) { for(;;) __asm__ volatile("nop":::"memory"); }
static void passes(uint16_t duration) {
    static uint16_t fraction;
    uint32_t at=tick_ms();
    for(profile_pass=0;profile_pass==0 || (duration>1 && tick_ms()-at<duration);profile_pass++) {
        uint16_t ms; uint32_t io_at=timer_now_us(),io;
        fake_spi_bytes=fake_soft_bytes=profile_delay=0;
        profile_begin(); f0_task(); profile_end();
        /* The debugger supplies this pass's measured production+MCAL cycles,
         * including the same reserve as the CPU gate. Never a fixed 1-ms tick. */
        if(jitter_pattern<4) profile_cadence_us=(uint16_t)(1000u*scan_jitter_next(jitter_pattern,&jitter_index,&jitter_seed));
        if(profile_elapsed_us<profile_cadence_us) profile_elapsed_us=profile_cadence_us;
        if(profile_elapsed_us>20000u) { ++profile_errors;profile_failure|=8192; }
        /* Subtract any clock time already spent in the register model. */
        io=timer_now_us()-io_at;
        if(io>profile_elapsed_us) { ++profile_errors;profile_failure|=8192; }
        else profile_elapsed_us-=io;
        ms=(uint16_t)(profile_elapsed_us/1000u);
        fraction=(uint16_t)(fraction+profile_elapsed_us%1000u);
        if(fraction>=1000) { ++ms;fraction-=1000; }
        while(ms--) { fake_advance(1); keys_sample_isr(); }
    }
}
settings_t *app_profile_candidate(void);
#define cfg (*app_profile_candidate())
static calibration_t cal;
__attribute__((noinline)) static void fixture(void) {
    uint8_t ch,j;
    fake_reset(); memset(&cfg,0,sizeof cfg); memset(&cal,0,sizeof cal);
    cfg.board_type=cfg.channel_count=24; cfg.address=1; cfg.sequence=7; cal.bank_count=3;
    for(ch=0;ch<MAX_CHANNELS;ch++) {
        for(j=0;j<6;j++) cfg.ch[ch].name[j]=' ';
        cfg.ch[ch].band_C=2; cal.baseline_nV[ch]=CAL_MISSING;
        if(ch<24) {
            cfg.ch[ch].type=CH_TYPE_K; cfg.ch[ch].alarm_dC=800; cfg.ch[ch].trip_dC=1000;
            cfg.ch[ch].probe_limit_dC=12000; cal.baseline_nV[ch]=3200000; cal.tag[ch]=1;
        }
    }
    (void)set_pack(&cfg,fake_eeprom); (void)cal_pack(&cal,fake_eeprom+768);
}
bool profile_boot_ready(void);
static void healthy(void) {
    uint16_t wait;
    for(wait=0;wait<10000;wait++) {
        if(profile_boot_ready() && scan_last()->scan_no>=2 &&
           scan_last()->scan_validated && scan_last()->meas[0].flags==MEAS_VALID) return;
        passes(1);
    }
    ++profile_errors;profile_failure|=1024;
}
static void key_time(uint8_t n) {
    uint8_t i; for(i=0;i<n;i++) { fake_advance(1); keys_sample_isr(); }
    keys_task();
}
static void drain(void);
static void mixed(void) {
    uint16_t wait; uint8_t frames=0; uint32_t number,previous; bool preparing;
    fixture(); f0_init(); profile_phase=10; healthy();drain();
    (void)ui_key(KEY_SET_LONG); passes(1);
    for(wait=0;wait<4;wait++) { (void)ui_key(KEY_SET); passes(1); }
    (void)ui_key(KEY_SET); passes(1); (void)ui_key(KEY_SET); passes(1);
    number=scan_current()->scan_no;
    for(wait=0;wait<1600 && scan_current()->scan_no==number;wait++) passes(1);
    cfg=*app_settings(); cfg.ch[0].name[0]='M';
    if(wait==1600 || app_commit_settings(&cfg)!=RES_OK) { ++profile_errors;profile_failure|=1; }
    for(wait=0;wait<200 && frames<1;wait++) {
        passes(1); if(fake_soft_bytes==54) ++frames; /* sixth sensor, signature still pending */
    }
    preparing=ee_owner_busy() && ee_owner_phase()==STORE_PREPARE;
    fake_pin(board()->keys[3],false); key_time(8);
    /* Capture the first RDY before holding DATA through ACK fixture setup.
     * This is the same real driver latch used by scan_task's P3 polls. */
    for(wait=0;wait<69;wait++) {
        uint8_t bank,ready=0;
        for(bank=0;bank<3;bank++) if(ad_ready(bank)==RES_OK) ++ready;
        if(ready==3) break;
        key_time(1);
    }
    if(wait==69) { ++profile_errors;profile_failure|=2048; }
    key_time(50);
    previous=app_protection()->latest_scan[0];
    for(wait=0;wait<16;wait++) fake_uart_receive((uint8_t)wait,0);
    fake_spi_bytes=fake_soft_bytes=profile_delay=0; profile_phase=9; profile_pass=0;
    passes(1);
    if(fake_soft_bytes==6) profile_mixed|=1;
    if(app_protection()->latest_scan[0]!=previous &&
       app_protection()->latest_scan[0]==scan_current()->scan_no) profile_mixed|=2;
    if(app_ack_reason()==ACK_R5_SETTINGS) profile_mixed|=4;
    if(preparing && ee_owner_busy() && ee_owner_phase()==STORE_PREPARE) profile_mixed|=8;
    if(ui_current_screen()==UI_FIELDS) profile_mixed|=16;
    if(fake_uart_rx_count()==8) profile_mixed|=32;
    if(profile_mixed!=63) { ++profile_errors;profile_failure|=2; }
}
static void newest_trip_ack(bool fault) {
    uint16_t wait; uint8_t i,shift=fault?3:0; uint32_t completed,number;
    bool off=true; fault_code_t cause=fault?FC_C01_OPEN:FC_C10_OVER_TRIP;
    fixture(); f0_init(); profile_phase=10; healthy();
    fake_pin(board()->keys[3],false); passes(120);
    fake_pin(board()->keys[3],true); passes(750);
    for(wait=0;wait<2000 && !timer_run_active();wait++) passes(1);
    if(!timer_run_active()) { ++profile_errors;profile_failure|=fault?8:4;return; }
    for(wait=0;wait<7000;wait++) {
        if(scan_current()->scan_no!=scan_last()->scan_no &&
           app_protection()->latest_scan[0]!=scan_current()->scan_no &&
           (!fault || scan_current()->scan_no%8u==0)) break;
        passes(1);
    }
    if(wait==7000 || !timer_run_active()) { ++profile_errors;profile_failure|=fault?8:4; return; }
    completed=scan_last()->scan_no;
    /* K-type 143.7 C with 25 C CJ, through the fake ADC registers. */
    if(fault) { scan_test_hold_publish(true); fake_ad_code(0,14,0xFFFFFF); }
    else {
        emf_nV_t hot,cold; uint32_t code;
        (void)tc_dC_to_emf(CH_TYPE_K,1437,&hot); (void)tc_dC_to_emf(CH_TYPE_K,250,&cold);
        code=(uint32_t)(0x800000LL+(int64_t)(hot-cold)*32*8388608/2500000000LL);
        fake_ad_code(0,0,code); fake_ad_code(0,14,code+343597);
    }
    for(wait=0;wait<1000 && f0_mode()==RUN;wait++) passes(1);
    if(wait==1000 || f0_mode()!=TRIPPED || timer_run_active() || scan_last()->scan_no!=completed) {
        ++profile_errors;profile_failure|=fault?32:16; return;
    }
    number=scan_current()->scan_no; profile_phase=fault?13:12;
    key_time(20); passes(1);
    fake_pin(board()->keys[3],false); key_time(20); passes(1);
    for(i=0;i<3;i++) { key_time(20); passes(1); if(timer_run_active()) off=false; }
    if(app_ack_reason()==ACK_R4_CHANNEL && f0_mode()==TRIPPED &&
       scan_last()->scan_no==completed) profile_rearm|=(uint8_t)(1u<<shift);
    fake_pin(board()->keys[3],true);
    scan_test_hold_publish(false);
    for(wait=0;wait<1000 && scan_last()->scan_no!=number;wait++) {
        passes(1); if(timer_run_active()) off=false;
    }
    if(wait<1000 && scan_last()->scan_validated && f0_mode()==TRIPPED && off &&
       !app_output()->window_refresh) profile_rearm|=(uint8_t)(2u<<shift);
    if(app_protection()->first.code==cause && (fault ||
       (app_protection()->first.value_dC>=1436 && app_protection()->first.value_dC<=1437)))
        profile_rearm|=(uint8_t)(4u<<shift);
}
static void ui_save_profile(void) {
    uint8_t i; uint16_t wait;
    fixture(); f0_init(); profile_phase=10; healthy(); profile_phase=14;
    (void)ui_key(KEY_SET_LONG); passes(1);
    for(i=0;i<6;i++) { (void)ui_key(KEY_SET); passes(1); } /* PIN, CHANNELS, CH1 */
    for(i=0;i<2;i++) { (void)ui_key(KEY_DOWN); passes(1); }
    (void)ui_key(KEY_SET); passes(1); (void)ui_key(KEY_UP); passes(1);
    for(i=0;i<6;i++) { (void)ui_key(KEY_SET); passes(1); }
    (void)ui_key(KEY_ESC); passes(1); (void)ui_key(KEY_ESC); passes(1);
    (void)ui_key(KEY_SET); passes(1);
    for(wait=0;wait<3000 && !ee_owner_busy();wait++) passes(1);
    if(ui_current_screen()!=UI_SAVING || !ee_owner_busy()) { ++profile_errors;profile_failure|=128; }
}
static void scan_cadences(void) {
    uint8_t p; uint16_t wait; uint32_t last,first;
    fixture(); f0_init(); profile_phase=10;healthy();
    for(p=0;p<3;p++) fake_ad_ready(p,49); /* rounded worst conversion */
    for(p=0;p<3;p++) {
        profile_cadence_us=p==0?5000:p==1?10000:20000;
        profile_phase=(uint8_t)(15+p);last=first=scan_last()->scan_no;
        for(wait=0;wait<3000 && profile_scan_count[p]<3;wait++) {
            passes(1);
            if(scan_last()->scan_no==last) continue;
            last=scan_last()->scan_no;
            if(last<=first+1) continue; /* exclude the cadence transition scan */
            if(!scan_last()->scan_validated || scan_diagnostics()->duration_ms>=APP_SCAN_DEADLINE_MS) ++profile_errors;
            if(scan_diagnostics()->duration_ms>profile_scan_ms[p]) profile_scan_ms[p]=scan_diagnostics()->duration_ms;
            ++profile_scan_count[p];
        }
        if(profile_scan_count[p]!=3) ++profile_errors;
    }
    profile_cadence_us=0;
}
static void scan_jitters(void) {
    uint8_t p,b; uint16_t wait; uint32_t last,at;
    fixture(); f0_init();profile_phase=10;healthy();
    fake_pin(board()->keys[3],false);passes(120);
    fake_pin(board()->keys[3],true);passes(1400);
    if(!timer_run_active()) ++profile_errors;
    for(b=0;b<3;b++) fake_ad_ready(b,49);
    for(p=0;p<4;p++) {
        jitter_pattern=p;jitter_index=0;jitter_seed=0x24F70001UL;
        profile_phase=(uint8_t)(18+p);last=scan_last()->scan_no;at=scan_last()->completed_ms;
        scan_test_ref_due();
        for(wait=0;wait<4000 && profile_gap_count[p]<8;wait++) {
            passes(1);
            if(f0_mode()!=RUN || !timer_run_active()) ++profile_errors;
            if(fake_port(PORT_A)&8u) ++profile_ref_seen[p];
            if(scan_last()->scan_no!=last) {
                uint32_t gap=scan_last()->completed_ms-at;
                if(!scan_last()->scan_validated || gap>1100u || gap!=scan_diagnostics()->duration_ms) ++profile_errors;
                if(gap>profile_gap_ms[p]) profile_gap_ms[p]=(uint16_t)gap;
                ++profile_gap_count[p];last=scan_last()->scan_no;at=scan_last()->completed_ms;
            }
        }
        if(profile_gap_count[p]!=8 || !profile_ref_seen[p] ||
           !scan_diagnostics()->ref_test_ok || fault_latched_at(app_faults(),FC_G05_SCAN_DEADLINE,0)) ++profile_errors;
    }
    jitter_pattern=255;profile_cadence_us=0;
}
static void ref_retry(void) {
    uint8_t attempt;uint16_t wait,n;uint32_t at,last,low_at;bool stable,pulse;
    fixture();f0_init();profile_phase=10;healthy();
    fake_pin(board()->keys[3],false);passes(120);
    fake_pin(board()->keys[3],true);passes(1400);
    profile_cadence_us=20000;profile_phase=22;
    for(attempt=0;attempt<2;attempt++) {
        scan_test_ref_due();fake_pin(board()->refok,true);
        for(wait=0;wait<150 && f0_mode()==RUN;wait++) passes(1);
        stable=wait<150 && f0_mode()==TRIPPED && !timer_run_active() &&
            app_protection()->first.code==FC_G08_ENGREF_LOST;
        if(!attempt && stable) profile_ref_retry|=1;
        at=tick_ms();last=scan_last()->scan_no;n=0;
        while(tick_ms()-at<5000u) {
            passes(1);
            stable&=f0_mode()==TRIPPED && !timer_run_active() && !(fake_port(PORT_A)&8u);
            if(scan_last()->scan_no!=last) {
                last=scan_last()->scan_no;++n;stable&=!scan_last()->scan_validated;
            }
        }
        if(stable && n>=4 && !scan_diagnostics()->ref_test_ok) profile_ref_retry|=attempt?16:2;
        if(attempt) break; /* Held-high case must never validate or pulse. */
        fake_pin(board()->refok,false);at=tick_ms();pulse=false;low_at=0;
        for(wait=0;wait<150;wait++) {
            passes(1);stable&=f0_mode()==TRIPPED && !timer_run_active();
            if(fake_port(PORT_A)&8u) pulse=true;
            else if(pulse && !low_at) low_at=tick_ms();
            if(scan_last()->scan_no!=last) {
                last=scan_last()->scan_no;
                if(scan_diagnostics()->ref_test_ok) {
                    if(stable && pulse && low_at && tick_ms()-low_at>=20u && scan_last()->scan_validated)
                        profile_ref_retry|=4;
                    break;
                }
                stable&=!scan_last()->scan_validated;
            }
        }
        profile_ref_recovery_ms=(uint16_t)(tick_ms()-at);
        if(wait==150 || fault_active(app_faults(),FC_G08_ENGREF_LOST) ||
           !fault_latched_at(app_faults(),FC_G08_ENGREF_LOST,0)) ++profile_errors;
        fake_pin(board()->keys[3],false);passes(120);
        fake_pin(board()->keys[3],true);passes(1400);
        if(app_ack_reason()==ACK_NONE && f0_mode()==RUN && timer_run_active()) profile_ref_retry|=8;
    }
    profile_cadence_us=0;
    if(profile_ref_retry!=31) { ++profile_errors;profile_failure|=16384; }
}
static void drain(void) {
    uint16_t wait;
    for(wait=0;wait<20000 && (ee_owner_busy() || !ee_owner_events_drained());wait++) passes(1);
    if(wait==20000) ++profile_errors;
}
int main(void) {
    uint8_t ch; uint16_t wait;
    if(profile_retained!=0x6d) { ++profile_errors;profile_failure|=4096; }
    fixture();
    f0_init(); profile_phase=0; healthy();
    fake_pin(board()->keys[3],false); profile_phase=1; passes(120);
    fake_pin(board()->keys[3],true); profile_phase=2; passes(1500);
    /* Full channel fault fan-out in one pass, followed by durable queue writes. */
    for(ch=0;ch<24;ch++) (void)fault_raise((fault_registry_t *)app_faults(),FC_C01_OPEN,ch);
    profile_phase=3; passes(1800);drain();
    /* Names-only and protection commit command paths. */
    cfg=*app_settings(); cfg.ch[0].name[0]='X'; (void)app_commit_settings(&cfg);
    profile_phase=4; passes(1800);drain();
    cfg=*app_settings(); cfg.ch[0].trip_dC=1100; (void)app_commit_settings(&cfg);
    profile_phase=5; passes(1800);drain();
    /* Service passive, prompts and EEPROM scratch include formatted output. */
    fake_reset(); (void)set_pack(&cfg,fake_eeprom); (void)cal_pack(&cal,fake_eeprom+768);
    fake_pin(board()->keys[2],false); f0_init(); profile_phase=6; passes(12000);
    fake_pin(board()->keys[2],true); passes(220);
    /* Exercise the most expensive pure commit: calibration invalidation on
     * type-epoch wrap, coincident with a full CJ transaction in the loop. */
    fixture(); cfg.ch[0].type_epoch=63; cal.tag[0]=253;
    (void)set_pack(&cfg,fake_eeprom); (void)cal_pack(&cal,fake_eeprom+768);
    f0_init(); profile_phase=7; healthy();drain();
    for(wait=0;wait<1600;wait++) { passes(1); if(fake_soft_bytes>=6) break; }
    cfg=*app_settings(); cfg.ch[0].type_epoch=0; cfg.ch[0].type=CH_TYPE_J;
    if(app_commit_settings(&cfg)!=RES_OK) ++profile_errors;
    profile_phase=8; passes(1800);drain();
    mixed();
    { char frame[80]; memset(frame,'X',sizeof frame); lcd_frame(frame); profile_phase=11; passes(96); }
    newest_trip_ack(false); newest_trip_ack(true);
    if(profile_rearm!=63) { ++profile_errors;profile_failure|=64; }
    ui_save_profile();scan_cadences();scan_jitters();ref_retry();
    app_stack_refresh(); profile_stack=app_stack_highwater();
    profile_stack_capacity=app_stack_capacity(); profile_done();
}
