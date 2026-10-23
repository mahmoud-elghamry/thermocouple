#include "fake_ui.h"
#include "mcal/timer.h"
#include <string.h>
settings_t fake_settings, fake_candidate;
prot_state_t fake_protection;
prot_out_t fake_output;
scan_out_t fake_scan;
fault_registry_t fake_faults;
uint32_t fake_ms;
unsigned fake_commits, fake_frames;
res_t fake_commit_result;
char fake_frame[80];
bool fake_repeat;
static ack_reason_t reason;
const settings_t *app_settings(void) { return &fake_settings; }
const prot_state_t *app_protection(void) { return &fake_protection; }
const prot_out_t *app_output(void) { return &fake_output; }
const fault_registry_t *app_faults(void) { return &fake_faults; }
ack_reason_t app_ack_reason(void) { return reason; }
const scan_out_t *scan_last(void) { return &fake_scan; }
uint32_t tick_ms(void) { return fake_ms; }
#ifndef UI_REAL_KEYS
void keys_repeat(bool b) { fake_repeat=b; }
#endif
void lcd_frame(const char f[80]) { memcpy(fake_frame,f,80); fake_frames++; }
res_t app_commit_settings(const settings_t *s) {
    fake_commits++;
    if(!s || s->board_type!=fake_settings.board_type || s->channel_count!=fake_settings.channel_count || set_validate(s)!=RES_OK) return RES_ERR_RANGE;
    if(fake_commit_result==RES_OK && s!=&fake_candidate) fake_candidate=*s;
    return fake_commit_result;
}
void fake_ack(ack_reason_t result) { reason=result;ui_ack_result(result); }
static void pass(void) {
#ifdef UI_PROFILE
    extern void ui_profile_begin(void),ui_profile_end(void);
    ui_profile_begin(); ui_task(1000); ui_profile_end();
#else
    ui_task(1000);
#endif
}
void fake_pump(void) { unsigned i; for(i=0;i<48;i++) { pass(); fake_ms++; } }
void fake_key(key_t k) { (void)ui_key(k); pass(); fake_ms++; fake_pump(); }
void fake_finish(res_t r) {
    if(r==RES_OK) { fake_settings=fake_candidate; fake_settings.sequence++; }
    ui_store_result(r); fake_pump();
}
void fake_reset(bool blank) {
    unsigned i;
    memset(&fake_settings,0,sizeof fake_settings);
    memset(&fake_scan,0,sizeof fake_scan);
    memset(&fake_protection,0,sizeof fake_protection);
    memset(&fake_output,0,sizeof fake_output);
    fault_init(&fake_faults);
    fake_ms=100; fake_commits=fake_frames=0; fake_commit_result=RES_OK;
    fake_settings.board_type=24; fake_settings.channel_count=24;
    fake_settings.address=1; fake_settings.sequence=7;
    fake_settings.pin_bcd=blank?0:0x1234;
    fake_protection.mode=blank?CONFIG_LOCK:RUN;
    fake_scan.scan_no=1234;
    for(i=0;i<24;i++) {
        chan_cfg_t *c=&fake_settings.ch[i];
        c->type=CH_TYPE_K; c->mode=CH_MODE_TRIP; memcpy(c->name,"CYL3B ",6);
        c->alarm_dC=4800; c->trip_dC=5200; c->probe_limit_dC=10000; c->band_C=5;
        fake_scan.meas[i].flags=MEAS_VALID; fake_scan.meas[i].temp_dC=5120;
        fake_scan.meas[i].scan_no=1234;
        if(blank) { memset(c,0,sizeof *c); }
    }
    if(blank) (void)fault_raise(&fake_faults,FC_G01_SETTINGS_INVALID,0);
    reason=ACK_NONE; ui_init(); ui_bind_candidate(&fake_candidate); fake_pump();
}
