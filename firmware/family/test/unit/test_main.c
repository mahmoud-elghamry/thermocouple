#include "app/service.h"
#include "services/scan.h"
#include "drivers/keys.h"
#include "mcal/timer.h"
#include "fake_hw.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)) { printf("main FAIL %d %s\n",__LINE__,#x); exit(1); } } while(0)
static void loop(unsigned n) { unsigned i; for(i=0;i<n;i++) { keys_sample_isr(); f0_task(); fake_advance(1); } }
static void fixture(void) {
    settings_t s; calibration_t cal; uint8_t bytes[SETTINGS_SLOT_SIZE]; unsigned i;
    /* Same test-only limits as Lane B's fixture_settings; never production defaults. */
    memset(&s,0,sizeof s); s.board_type=24; s.channel_count=24; s.address=1; s.pin_bcd=0x1234; s.sequence=7;
    for(i=0;i<MAX_CHANNELS;i++) { memcpy(s.ch[i].name,"      ",6); s.ch[i].band_C=2; }
    s.ch[0].type=CH_TYPE_K; s.ch[0].alarm_dC=800; s.ch[0].trip_dC=1000; s.ch[0].probe_limit_dC=12000;
    CHECK(set_pack(&s,bytes)==RES_OK); memcpy(fake_eeprom+0x40,bytes,SETTINGS_SLOT_SIZE);
    s.sequence=8; CHECK(set_pack(&s,bytes)==RES_OK); memcpy(fake_eeprom+0x340,bytes,SETTINGS_SLOT_SIZE);
    memset(&cal,0,sizeof cal); cal.bank_count=3;
    for(i=0;i<MAX_CHANNELS;i++) cal.baseline_nV[i]=CAL_MISSING;
    cal.baseline_nV[0]=3200000; cal.tag[0]=1; CHECK(cal_pack(&cal,bytes)==RES_OK);
    memcpy(fake_eeprom+0x640,bytes,CAL_SLOT_SIZE);
}
void test_main(void) {
    fake_reset(); fixture(); f0_init(); loop(3000);
    CHECK(f0_mode()==1); CHECK(scan_last()->settings_seq==8); CHECK(!timer_run_active());
    fake_pin(board()->keys[3],false); loop(100); CHECK(f0_mode()==1 && !timer_run_active());
    CHECK(fake_feeds>1000);
    fake_reset(); fixture(); fake_eeprom[0x340]=0; f0_init(); loop(3000);
    CHECK(scan_last()->settings_seq==7); CHECK(f0_mode()==1 && !timer_run_active());
    fake_reset(); f0_init(); loop(3000); CHECK(f0_mode()==4 && !timer_run_active());
    fake_reset(); fixture(); fake_pin(board()->keys[2],false); f0_init(); loop(3000);
    CHECK(f0_mode()==4 && !timer_run_active());
    fake_reset(); fixture(); fake_pin(board()->keys[2],false); fake_pin(board()->keys[3],false);
    f0_init(); loop(3000); CHECK(f0_mode()==1 && !timer_run_active());
    printf("main: %u checks PASS\n",checks);
}
