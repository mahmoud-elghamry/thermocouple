/* AVR instruction simulator harness: real shell and drivers, register fakes.
 * No WDR instruction: the GNU simulator does not implement it. */
#include "app/app.h"
#include "app/ee_owner.h"
#include "app/service.h"
#include "services/scan.h"
#include "drivers/keys.h"
#include "mcal/timer.h"
#include "mcal/flash_crc.h"
#include "fake_hw.h"
#include <string.h>
volatile uint16_t profile_pass;
volatile uint8_t profile_phase;
volatile uint32_t profile_delay;
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
__attribute__((noinline)) void profile_begin(void) { __asm__ volatile("nop"); }
__attribute__((noinline)) void profile_end(void) { __asm__ volatile("nop"); }
__attribute__((noinline)) void profile_done(void) { for(;;) __asm__ volatile("nop"); }
static void passes(uint16_t n) {
    for(profile_pass=0;profile_pass<n;profile_pass++) {
        bool measure=(profile_phase==2 && profile_pass<750) || (profile_phase==3 && profile_pass==0) ||
            ((profile_phase==4 || profile_phase==5 || profile_phase==8) && profile_pass<20) ||
            (profile_phase==0 && profile_pass==430) || (profile_phase==1 && profile_pass==58) ||
            (profile_phase==6 && profile_pass==652);
        fake_spi_bytes=fake_soft_bytes=profile_delay=0;
        if(measure) profile_begin();
        f0_task();
        if(measure) profile_end();
        fake_advance(1); keys_sample_isr();
    }
}
static settings_t cfg;
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
int main(void) {
    uint8_t ch; uint16_t wait;
    fixture();
    f0_init(); profile_phase=0; passes(3100);
    fake_pin(board()->keys[3],false); profile_phase=1; passes(70);
    fake_pin(board()->keys[3],true); profile_phase=2; passes(1500);
    /* Full channel fault fan-out in one pass, followed by durable queue writes. */
    for(ch=0;ch<24;ch++) (void)fault_raise((fault_registry_t *)app_faults(),FC_C01_OPEN,ch);
    profile_phase=3; passes(1800);
    /* Names-only and protection commit command paths. */
    cfg=*app_settings(); cfg.ch[0].name[0]='X'; (void)app_commit_settings(&cfg);
    profile_phase=4; passes(1800);
    cfg=*app_settings(); cfg.ch[0].trip_dC=1100; (void)app_commit_settings(&cfg);
    profile_phase=5; passes(1800);
    /* Service passive, prompts and EEPROM scratch include formatted output. */
    fake_reset(); (void)set_pack(&cfg,fake_eeprom); (void)cal_pack(&cal,fake_eeprom+768);
    fake_pin(board()->keys[2],false); f0_init(); profile_phase=6; passes(12000);
    fake_pin(board()->keys[2],true); passes(220);
    /* Exercise the most expensive pure commit: calibration invalidation on
     * type-epoch wrap, coincident with a full CJ transaction in the loop. */
    fixture(); cfg.ch[0].type_epoch=63; cal.tag[0]=253;
    (void)set_pack(&cfg,fake_eeprom); (void)cal_pack(&cal,fake_eeprom+768);
    f0_init(); profile_phase=7; passes(3000);
    for(wait=0;wait<1600;wait++) { passes(1); if(fake_soft_bytes==30) break; }
    cfg=*app_settings(); cfg.ch[0].type_epoch=0; cfg.ch[0].type=CH_TYPE_J;
    (void)app_commit_settings(&cfg); profile_phase=8; passes(20);
    profile_done();
}
