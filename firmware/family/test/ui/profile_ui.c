#include "fake_ui.h"
#include <string.h>
volatile uint8_t profile_case;
void __attribute__((noinline)) ui_profile_begin(void) { __asm__ volatile("nop"); }
void __attribute__((noinline)) ui_profile_end(void) { __asm__ volatile("nop"); }
void __attribute__((noinline)) ui_profile_done(void) { __asm__ volatile("nop"); }
int main(void) {
    unsigned i;
    profile_case=0;fake_reset(false);fake_settings.pin_bcd=0;
    profile_case=1;fake_key(KEY_SET_LONG);for(i=0;i<4;i++) fake_key(KEY_SET);
    profile_case=2;fake_key(KEY_SET);fake_key(KEY_SET);
    for(i=0;i<4;i++) fake_key(KEY_DOWN);
    fake_key(KEY_SET);fake_key(KEY_DOWN);fake_key(KEY_SET);
    profile_case=3;fake_key(KEY_ESC);fake_key(KEY_ESC);
    profile_case=4;fake_key(KEY_SET);
    profile_case=5;fake_finish(RES_OK);
    profile_case=6;fake_scan.scan_no=UINT32_MAX;fake_pump();
    profile_case=7;for(i=0;i<4;i++) fake_key(KEY_DOWN);
    { event_t e;memset(&e,0,sizeof e);e.type=EV_TRIP;e.power_cycles=99;e.uptime_s=0xFFFFFF;
      e.channel=3;e.value_dC=13720;ui_event_result(0,32,RES_OK,&e);fake_pump(); }
    profile_case=8;fake_reset(true);fake_key(KEY_SET_LONG);for(i=0;i<4;i++) fake_key(KEY_SET);
    profile_case=9;
    { ui_state_t u;ui_begin(&u,&fake_settings,false);u.diff=0;
      for(i=0;i<24;i++) { u.work[i].type=2;u.work[i].mode=1;u.work[i].name[0]='X';
        u.work[i].alarm=10;u.work[i].trip=20;u.work[i].limit=1000;u.work[i].band=50; }
      u.address=247;u.baud=1;u.work_pin=0x9999;
      for(i=0;i<171;i++) { ui_profile_begin();(void)ui_find_diff(&u,&fake_settings,1);ui_profile_end(); }
      for(i=0;i<171;i++) { ui_profile_begin();(void)ui_find_diff(&u,&fake_settings,-1);ui_profile_end(); }
    }
    profile_case=10;fake_reset(false);
    for(i=0;i<24;i++) { fake_protection.alarm_latch[i]=1;fake_scan.meas[i].temp_dC=13720; }
    ui_alarm_snapshot(24,FC_C11_OVER_ALARM,3,0);fake_pump();
    profile_case=11;fake_key(KEY_SET);fake_key(KEY_SET);ui_detail_stats(-2000,13720,-5);fake_pump();
    profile_case=12;
    (void)fault_raise(&fake_faults,FC_B15_ADC_RESET,95);
    for(i=1;i<=6;i++) { fake_ack((ack_reason_t)i);fake_pump(); }
    profile_case=13;fake_reset(false);for(i=0;i<4;i++) fake_key(KEY_DOWN);
    { event_t e;memset(&e,0,sizeof e);e.type=EV_FAULT;e.power_cycles=65535;e.uptime_s=0xFFFFFF;
      e.code=FC_B06_REF;e.unit=3;ui_event_result(0,32,RES_OK,&e);fake_pump(); }
    ui_profile_done();return 0;
}
