#include "services/scan.h"
#include "app/timing.h"
#include "drivers/ad7124.h"
#include "drivers/tmp126.h"
#include "drivers/iso_spi.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "fake_hw.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)) { printf("scan FAIL %d %s\n",__LINE__,#x); exit(1); } } while(0)
static settings_t cfg;
static calibration_t cal;
static fault_registry_t faults;
static void setup(void) {
    uint8_t i;
    fake_reset(); gpio_init(); timer_init(); iso_init();
    memset(&cfg,0,sizeof cfg); memset(&cal,0,sizeof cal); fault_init(&faults);
    cfg.sequence=7; cfg.board_type=24; cfg.channel_count=24; cal.bank_count=3;
    for(i=0;i<24;i++) { cfg.ch[i].type=CH_TYPE_K; cal.baseline_nV[i]=3200000; cal.tag[i]=1; }
    scan_init(&cfg,&cal,&faults);
}
static void next_scan(void) {
    uint32_t n=scan_last()->scan_no; unsigned i;
    for(i=0;i<3000 && scan_last()->scan_no==n;i++) { scan_task(); fake_advance(1); }
    CHECK(scan_last()->scan_no!=n);
}
static uint32_t from_nV(int32_t v,uint8_t gain) { return (uint32_t)(0x800000L+((int64_t)v*gain*8388608/2500000000LL)); }
static void boundaries(void) {
    static const struct { uint8_t slot,gain; int32_t lo,hi; fault_code_t fault; } tests[]={
        {9,32,-50000,50000,FC_B08_ZERO},{10,32,15000000,25000000,FC_B09_GAIN},
        {12,1,525000000,575000000,FC_B07_AVDD}
    };
    unsigned i; uint32_t lo,hi,nom;
    for(i=0;i<3;i++) {
        lo=from_nV(tests[i].lo,tests[i].gain); hi=from_nV(tests[i].hi,tests[i].gain);
        CHECK(scan_limit(tests[i].slot,lo+1,0,0,0,0)==FC_NONE);
        CHECK(scan_limit(tests[i].slot,lo-1,0,0,0,0)==tests[i].fault);
        CHECK(scan_limit(tests[i].slot,hi-1,0,0,0,0)==FC_NONE);
        CHECK(scan_limit(tests[i].slot,hi+1,0,0,0,0)==tests[i].fault);
    }
    nom=from_nV(20000000,32);
    CHECK(scan_limit(11,from_nV(19910000,1),nom,0,0,0)==FC_NONE);
    CHECK(scan_limit(11,from_nV(19890000,1),nom,0,0,0)==FC_B09_GAIN);
    CHECK(scan_limit(11,from_nV(20090000,1),nom,0,0,0)==FC_NONE);
    CHECK(scan_limit(11,from_nV(20110000,1),nom,0,0,0)==FC_B09_GAIN);
    CHECK(scan_limit(13,0x800000+419431,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(13,0x800000+419430,0,0,0,0)==FC_C03_COMMON_MODE);
    CHECK(scan_limit(13,0x800000+7969177,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(13,0x800000+7969178,0,0,0,0)==FC_C03_COMMON_MODE);
    CHECK(scan_limit(14,from_nV(1600100,32),0,0,3200000,0x800000)==FC_NONE);
    CHECK(scan_limit(14,from_nV(1599900,32),0,0,3200000,0x800000)==FC_C06_SHORTED);
    CHECK(scan_limit(14,from_nV(6399900,32),0,0,3200000,0x800000)==FC_NONE);
    CHECK(scan_limit(14,from_nV(6400100,32),0,0,3200000,0x800000)==FC_C01_OPEN);
    CHECK(scan_limit(0,0x800000+8220835,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(0,0x800000+8220836,0,0,0,0)==FC_C02_RANGE);
    CHECK(scan_limit(0,0x800000-8220835,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(0,0x800000-8220836,0,0,0,0)==FC_C02_RANGE);
    CHECK(scan_limit(8,0x800000+6878658,0,0,0,0)==FC_B06_REF);
    CHECK(scan_limit(8,0x800000+6878659,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(8,0x800000+7102355,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(8,0x800000+7102356,0,0,0,0)==FC_B06_REF);
}
void test_scan(void) {
    unsigned s,b; uint32_t normal[15];
    setup(); next_scan(); CHECK(scan_last()->scan_validated);
    CHECK(scan_last()->settings_seq==7); CHECK(scan_diagnostics()->duration_ms<=750);
    next_scan(); CHECK(scan_last()->meas[0].flags&MEAS_VALID);
    for(s=0;s<15;s++) normal[s]=scan_diagnostics()->raw[0][s];
    /* Every diagnostic window exercised by running the actual scanner with fake register conversions. */
    for(s=8;s<=12;s++) {
        fake_ad_code(0,(uint8_t)s,0xFFFFFF); next_scan(); CHECK(!scan_last()->scan_validated);
        fake_ad_code(0,(uint8_t)s,normal[s]); next_scan(); CHECK(scan_last()->scan_validated);
    }
    fake_tmp_reg(0,12,0); next_scan(); CHECK(fault_at(&faults,FC_B12_CJ_ONE,0));
    fake_tmp_reg(1,12,0); next_scan(); CHECK(fault_at(&faults,FC_B10_CJ_BOTH,0));
    fake_tmp_reg(0,12,0x2126); fake_tmp_reg(1,12,0x2126);
    fake_tmp_reg(0,0,0x0F00); next_scan(); CHECK(fault_at(&faults,FC_B11_CJ_DIFF,0));
    fake_tmp_reg(0,0,0x0C80); next_scan(); CHECK(scan_last()->scan_validated);
    fake_pin(board()->refok,true); next_scan(); CHECK(!scan_last()->scan_validated);
    fake_pin(board()->refok,false); next_scan(); CHECK(scan_last()->scan_validated);
    /* First observed conversion error is invalid even when ERROR is clear-on-read. */
    fake_ad_error(0,1UL<<17); next_scan(); CHECK(!(scan_last()->meas[0].flags&MEAS_VALID));
    CHECK(scan_last()->meas[0].flags&MEAS_RANGE);
    next_scan(); CHECK(scan_last()->meas[0].flags&MEAS_VALID);
    fake_ad_por(0,true); next_scan(); CHECK(!scan_last()->scan_validated);
    next_scan(); CHECK(scan_last()->scan_validated);
    for(b=0;b<3;b++) fake_ad_crc((uint8_t)b,255);
    next_scan(); CHECK(!scan_last()->scan_validated);
    CHECK(scan_emf(0x800000,32)==0);
    CHECK(scan_limit(8,0xEAAAAB,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(8,0xEAAAAB,0,CAL_MISSING,0,0)==FC_B06_REF);
    CHECK(scan_limit(9,0x800000,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(10,normal[10],0,0,0,0)==FC_NONE);
    CHECK(scan_limit(11,normal[11],normal[10],0,0,0)==FC_NONE);
    CHECK(scan_limit(13,0x800000,0,0,0,0)==FC_C03_COMMON_MODE);
    CHECK(scan_limit(13,0xC00000,0,0,0,0)==FC_NONE);
    CHECK(scan_limit(14,0x800000,0,0,3200000,0x800000)==FC_C06_SHORTED);
    CHECK(scan_limit(14,0xFFFFFF,0,0,3200000,0x800000)==FC_C01_OPEN);
    CHECK(scan_limit(14,normal[14],0,0,CAL_MISSING,0x800000)==FC_G10_CALIBRATION);
    boundaries(); setup(); next_scan(); fake_fuses[1]=0xD1; next_scan();
    CHECK(!scan_last()->scan_validated && fault_active(&faults,FC_G15_FUSES));
    fake_fuses[1]=0xC1; next_scan(); CHECK(!scan_last()->scan_validated); /* requires reset/reprogram */
    setup(); next_scan(); scan_task(); /* 03 section 10.2: delay beyond the explicit 1200-ms deadline,
     * independent of how many scheduler passes remain after the stall. */
    fake_advance(APP_SCAN_DEADLINE_MS+1u); next_scan();
    CHECK(!scan_last()->scan_validated && fault_active(&faults,FC_G05_SCAN_DEADLINE));
    setup(); fake_ref_follow=false; next_scan();
    CHECK(!scan_last()->scan_validated && fault_active(&faults,FC_G09_ENGREF_TEST));
    CHECK(fake_bus_errors==0);
    printf("scan: %u checks PASS\n",checks);
}
