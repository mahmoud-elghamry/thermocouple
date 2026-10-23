#include "app/service.h"
#include "app/image_identity.h"
#include "drivers/keys.h"
#include "drivers/rs485.h"
#include "drivers/iso_spi.h"
#include "services/scan.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "fake_hw.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)) { printf("service FAIL %d %s\n",__LINE__,#x); exit(1); } } while(0)
static void loop(unsigned count) {
    unsigned i; for(i=0;i<count;i++) {
        scan_task(); keys_sample_isr(); keys_task(); svc_task(); rs485_task(); fake_advance(1);
    }
}
static void confirm(void) {
    fake_pin(board()->keys[2],false); loop(30);
    fake_pin(board()->keys[2],true); loop(220);
}
void test_service(void) {
    static settings_t cfg; static calibration_t cal; static fault_registry_t faults;
    unsigned i;
    fake_reset(); gpio_init(); iso_init(); keys_init(); rs485_init(); fault_init(&faults);
    memset(&cfg,0,sizeof cfg); memset(&cal,0,sizeof cal); cfg.channel_count=24; cfg.board_type=24; cal.bank_count=3;
    for(i=0;i<24;i++) { cal.baseline_nV[i]=CAL_MISSING; cal.tag[i]=0; }
    scan_init(NULL,&cal,&faults); svc_init(&cfg,&cal,false,false,false,2,true);
    loop(12000); CHECK(svc_active_step()==1); CHECK(!timer_run_active());
    CHECK(strstr(fake_uart_log,"P01 BOARD")!=NULL); CHECK(strstr(fake_uart_log,"P16 LOOP")!=NULL);
    {
        image_identity_t id;char expected[100];app_identity_read(&id);
        CHECK(sizeof id==APP_IDENTITY_BYTES && !memcmp(id.magic,APP_IDENTITY_MAGIC,8));
        (void)snprintf(expected,sizeof expected,"P01 BOARD %u v%u.%u.%u %s %s MCU %02X%02X%02X OK",
            id.board,id.major,id.minor,id.patch,id.commit,id.dirty?"DIRTY":"CLEAN",id.mcu[0],id.mcu[1],id.mcu[2]);
        CHECK(strstr(fake_uart_log,expected)!=NULL);
    }
    CHECK(strstr(fake_uart_log,"P16 STACK_BYTES 0 OK")!=NULL);
    confirm(); /* A01: every requested key must also be released. */
    for(i=0;i<4;i++) {
        fake_pin(board()->keys[i],false); loop(220); CHECK(svc_active_step()==1);
        fake_pin(board()->keys[i],true); loop(220);
    }
    fake_pin(board()->keys[0],false); fake_pin(board()->keys[1],false); loop(30);
    fake_pin(board()->keys[0],true); fake_pin(board()->keys[1],true); loop(300);
    CHECK(svc_active_step()==2);
    confirm(); CHECK((fake_port(PORT_C)&0x40)!=0); loop(1200);
    CHECK(svc_active_step()==3); CHECK(!timer_run_active());
    fake_pin(board()->keys[2],false); loop(50); CHECK(!timer_run_active());
    fake_pin(board()->keys[2],true); loop(30); CHECK(timer_run_active());
    fake_advance(1000); CHECK(!timer_run_active()); loop(150);
    CHECK(svc_active_step()==4); CHECK(!timer_run_active());
    confirm(); CHECK((fake_port(PORT_B)&8)!=0); CHECK(!timer_run_active()); loop(1200);
    CHECK(svc_active_step()==5); CHECK((fake_port(PORT_B)&8)==0);
    fake_eeprom[0x40]=0x12; fake_eeprom[0x340]=0x34;
    confirm(); loop(1200); CHECK(svc_active_step()==6);
    for(i=0xF00;i<0x1000;i++) CHECK(fake_eeprom[i]==0xFF);
    CHECK(fake_eeprom[0x40]==0x12 && fake_eeprom[0x340]==0x34);
    confirm(); loop(14000); CHECK(svc_active_step()==7); CHECK(cal_validate(&cal)==RES_OK);
    CHECK(cal.ref_ppm[0]>=-10000 && cal.ref_ppm[0]<=10000);
    CHECK(cal.baseline_nV[0]==CAL_MISSING);
    confirm(); confirm(); loop(66000); CHECK(svc_finished());
    CHECK(cal.baseline_nV[0]>=1500000 && cal.baseline_nV[0]<=10000000 && cal.tag[0]==1);
    CHECK(strstr(fake_uart_log,"END ")!=NULL); CHECK(!timer_run_active());
    printf("service: %u checks PASS\n",checks);
}
