#include "app/app.h"
#include "app/ui.h"
#include "app/modbus.h"
#include "app/ee_owner.h"
#include "app/version.h"
#include "app/service.h"
#include "services/scan.h"
#include "services/tc_math.h"
#include "mcal/timer.h"
#include "mcal/gpio.h"
#include "fake_hw.h"
#include "model.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)) { printf("F4 FAIL %u: %s mode=%u step=%u t=%lu\n%s\n",__LINE__,#x,f0_mode(),svc_active_step(),(unsigned long)tick_ms(),fake_uart_log); exit(1); } } while(0)
static void loop(unsigned n) { unsigned i; for(i=0;i<n;i++) { f0_task(); fake_advance(1); CHECK(!model_watchdog_reset()); } }
static void key(key_t k) {
    unsigned p=k==KEY_UP?0:k==KEY_DOWN?1:2;
    if(k==KEY_ESC) { fake_pin(board()->keys[0],false); fake_pin(board()->keys[1],false); }
    else fake_pin(board()->keys[p],false);
    loop(k==KEY_SET_LONG?3010:30);
    if(k==KEY_ESC) { fake_pin(board()->keys[0],true); fake_pin(board()->keys[1],true); }
    else fake_pin(board()->keys[p],true);
    loop(k==KEY_UP || k==KEY_DOWN?180:30);
}
static void times(key_t k,unsigned n) { while(n--) key(k); }
static void pin(uint16_t value) { int shift; for(shift=12;shift>=0;shift-=4) { times(KEY_UP,(value>>shift)&15u); key(KEY_SET); } }
static void ack(void) { fake_pin(board()->keys[3],false); loop(70); fake_pin(board()->keys[3],true); loop(20); }
static void cool_settle(void) {
    unsigned i;
    fake_ad_code(0,0,0x800000); fake_ad_code(0,14,0x853E2D); loop(1500);
    /* 03 section 4.1: a step between TC and burnout can latch C01/C06.
     * F7 changes that alignment. Wait for its owning-channel check (8 scans),
     * preserving every trip/ACK assertion instead of relying on phase luck. */
    for(i=0;i<8000 && (fault_active(app_faults(),FC_C01_OPEN) || fault_active(app_faults(),FC_C06_SHORTED));i++) loop(1);
    CHECK(i<8000 && scan_last()->scan_validated);
}
static void commissioning(void) {
    unsigned i;
    fake_reset(); f0_init(); loop(3000); CHECK(f0_mode()==CONFIG_LOCK);
    key(KEY_SET_LONG); pin(0); pin(0x1111); pin(0x1111);
    key(KEY_SET); key(KEY_SET); key(KEY_SET); key(KEY_UP); key(KEY_SET); /* CH1 K */
    times(KEY_DOWN,6); key(KEY_SET); times(KEY_UP,11); key(KEY_SET); /* 200 C limit */
    times(KEY_UP,3); key(KEY_SET); times(KEY_UP,50); key(KEY_SET); /* alarm 50 C */
    key(KEY_DOWN); key(KEY_SET); times(KEY_UP,60); key(KEY_SET); /* trip 60 C */
    key(KEY_ESC); key(KEY_ESC); key(KEY_SET); loop(4000);
    CHECK(ee_owner_settings_valid() && app_settings()->pin_bcd==0x1111);
    CHECK(app_settings()->ch[0].type==CH_TYPE_K && app_settings()->ch[0].trip_dC==600);
    CHECK(f0_mode()==CONFIG_LOCK); /* 06 section 6: calibration is a service operation. */
    CHECK(!fault_active(app_faults(),FC_G01_SETTINGS_INVALID));
    CHECK(fault_active(app_faults(),FC_G10_CALIBRATION));
    key(KEY_SET_LONG); pin(0); CHECK(ui_current_screen()==UI_PIN);
    pin(0x1111); CHECK(ui_current_screen()==UI_SETUP);
    key(KEY_SET); key(KEY_SET);
    CHECK(ui_test_state()->work[0].type==CH_TYPE_K && ui_test_state()->work[0].trip==600);
    key(KEY_ESC); key(KEY_ESC); key(KEY_ESC); CHECK(ui_current_screen()==UI_HOME);
    fake_pin(board()->keys[2],false); f0_init(); loop(12000);
    fake_pin(board()->keys[2],true); loop(1000); CHECK(f0_mode()==SERVICE);
    for(i=0;i<5;i++) { CHECK(svc_active_step()==i+1); key(KEY_ESC); loop(250); }
    CHECK(svc_active_step()==6); key(KEY_SET); loop(16000); CHECK(svc_active_step()==7);
    key(KEY_SET); loop(1000); key(KEY_SET); loop(52000); CHECK(svc_finished() && ee_owner_cal_saved());
    f0_init(); loop(3000); CHECK(f0_mode()==START_LATCHED); ack(); loop(750); CHECK(timer_run_active());
    /* Configure 19200 through the real UI before the garbage-flood test. */
    key(KEY_SET_LONG); pin(0x1111); key(KEY_DOWN); key(KEY_SET); key(KEY_DOWN); key(KEY_SET);
    key(KEY_UP); key(KEY_SET); key(KEY_ESC); key(KEY_ESC); key(KEY_SET); loop(4000);
    CHECK(app_settings()->baud==1 && f0_mode()==RUN && timer_run_active());
}
static unsigned request(uint16_t base,uint16_t count,uint8_t *reply) {
    uint8_t q[8]={1,4,0,0,0,0,0,0}; uint16_t crc; unsigned i,n;
    q[2]=(uint8_t)(base>>8); q[3]=(uint8_t)base; q[4]=(uint8_t)(count>>8); q[5]=(uint8_t)count;
    crc=mb_crc16(q,6); q[6]=(uint8_t)crc; q[7]=(uint8_t)(crc>>8);
    fake_uart_clear(); loop(10);
    for(i=0;i<8;i++) { fake_uart_receive(q[i],0); delay_us(app_settings()->baud?600:1200); }
    for(i=0;i<250 && !fake_uart_tx_size();i++) loop(1);
    loop(100); n=fake_uart_tx_size(); CHECK(n<=133 && n>=5);
    memcpy(reply,fake_uart_log,n); CHECK(mb_crc16(reply,(uint16_t)n)==0); return n;
}
static uint16_t word(const uint8_t *p,unsigned i) { return (uint16_t)((uint16_t)p[3+2*i]<<8|p[4+2*i]); }
static void communication(void) {
    uint8_t reply[133]; unsigned n,i,load; uint32_t at,code,delay[2]; emf_nV_t hot,cold;
    n=request(100,10,reply); CHECK(n==25 && word(reply,0)>=249 && word(reply,0)<=250);
    CHECK(word(reply,3)==CH_TYPE_K && word(reply,6)==600);
    n=request(0,20,reply); CHECK(n==45 && word(reply,0)==1 && word(reply,3)==FW_BUILD_VERSION && word(reply,5)==SETTINGS_SCHEMA_VERSION);
    CHECK(word(reply,6)==RUN && word(reply,7)==1 && word(reply,8)==1);
    /* Same fake ADC step and scan phase with/without continuous garbage. */
    CHECK(tc_dC_to_emf(CH_TYPE_K,1437,&hot)==RES_OK && tc_dC_to_emf(CH_TYPE_K,250,&cold)==RES_OK);
    code=(uint32_t)(0x800000LL+(int64_t)(hot-cold)*32*8388608/2500000000LL);
    for(load=0;load<2;load++) {
        uint32_t number;
        if(load) {
            cool_settle(); ack(); loop(750);
            for(i=0;i<600000;i++) {
                fake_uart_receive((uint8_t)i,0); fake_uart_receive((uint8_t)~i,0);
                loop(1); CHECK(timer_run_active());
            }
        }
        CHECK(timer_run_active());
        number=scan_current()->scan_no;
        for(i=0;i<800 && scan_current()->scan_no==number;i++) loop(1);
        CHECK(i<800); at=tick_ms(); fake_ad_code(0,0,code); fake_ad_code(0,14,code+343597);
        for(i=0;i<1000 && timer_run_active();i++) {
            if(load) { fake_uart_receive((uint8_t)i,0); fake_uart_receive((uint8_t)~i,0); }
            loop(1);
        }
        delay[load]=tick_ms()-at;
        CHECK(!timer_run_active() && f0_mode()==TRIPPED && delay[load]<=1000);
    }
    printf("F4 trip baseline/flood: %lu/%lu ms (19200 baud)\n",(unsigned long)delay[0],(unsigned long)delay[1]);
    CHECK((delay[0]>delay[1]?delay[0]-delay[1]:delay[1]-delay[0])<=2);
    CHECK(app_protection()->first.code==FC_C10_OVER_TRIP);
    { mb_status_t status; mb_io_status(&status); CHECK(status.uptime_s>=600 && !status.run_driven); }
    n=request(10,4,reply); CHECK(n==13 && word(reply,0)==FC_C10_OVER_TRIP && word(reply,1)==1);
    CHECK(word(reply,2)==(uint16_t)app_protection()->first.value_dC && word(reply,3)==600);
    n=request(28,1,reply); CHECK(n==7 && (word(reply,0)&1u));
}
static void saves(void) {
    uint32_t seq; uint8_t reply[133];
    cool_settle();
    (void)request(28,1,reply); CHECK(word(reply,0)&1u); /* persists after recovery, before ACK */
    ack(); loop(750); CHECK(timer_run_active());
    (void)request(28,1,reply); CHECK(word(reply,0)==0);
    key(KEY_SET_LONG); pin(0x1111); key(KEY_SET); key(KEY_SET); times(KEY_DOWN,2); key(KEY_SET);
    key(KEY_UP); times(KEY_SET,6); key(KEY_ESC); key(KEY_ESC); key(KEY_SET); seq=app_settings()->sequence;
    loop(4000); CHECK(app_settings()->sequence==seq+1 && f0_mode()==RUN && timer_run_active());
    key(KEY_SET_LONG); pin(0x1111); key(KEY_SET); key(KEY_SET); times(KEY_DOWN,4); key(KEY_SET);
    key(KEY_UP); key(KEY_SET); key(KEY_ESC); key(KEY_ESC); key(KEY_SET); loop(4000);
    CHECK(f0_mode()==START_LATCHED && !timer_run_active() && app_settings()->ch[0].trip_dC==610);
}
static void recovery(void) {
    uint8_t i,n; event_t e; bool found=false;
    fake_pin(board()->keys[2],false); fake_pin(board()->keys[3],false); f0_init(); loop(3000);
    CHECK(f0_mode()==START_LATCHED && ui_current_screen()==UI_RECOVER && !timer_run_active());
    fake_pin(board()->keys[2],true); fake_pin(board()->keys[3],true); loop(30); key(KEY_SET); loop(4000);
    CHECK(app_settings()->pin_bcd==0 && f0_mode()==START_LATCHED && !timer_run_active());
    for(i=0;i<32;i++) if(ee_owner_history(i,&n,&e)==RES_OK && e.type==EV_PIN_RESET) found=true;
    CHECK(found);
    fake_reset(); fake_pin(board()->keys[2],false); fake_pin(board()->keys[3],false); f0_init(); loop(3000);
    CHECK(ui_current_screen()==UI_RECOVER && f0_mode()==CONFIG_LOCK);
    fake_pin(board()->keys[2],true); fake_pin(board()->keys[3],true); loop(30); key(KEY_SET); loop(1000);
    CHECK(ui_current_screen()==UI_HOME && f0_mode()==CONFIG_LOCK && !timer_run_active());
}
void test_f4(void) {
    commissioning(); communication(); saves(); recovery();
    printf("F4 integration: %u checks PASS (keys, commissioning, Modbus, flood, UI commits)\n",checks);
}
