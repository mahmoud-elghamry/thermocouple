#include "app/timing.h"
#include "drivers/keys.h"
#include "drivers/lcd.h"
#include "drivers/rs485.h"
#include "drivers/relays.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "fake_hw.h"
#include "app/outputs_hw.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)) { printf("peripherals FAIL %d %s\n",__LINE__,#x); exit(1); } } while(0)
static void step(unsigned ms) { unsigned i; for(i=0;i<ms;i++) { fake_advance(1); keys_sample_isr(); keys_task(); } }
static void key(uint8_t k,bool on) { fake_pin(board()->keys[k],!on); }
void test_peripherals(void) {
    char frame[80]; unsigned i;
    fake_reset(); gpio_init(); keys_init();
    key(3,true); step(100); CHECK(keys_get()==KEY_NONE); /* boot-held ACK */
    key(3,false); step(10); key(3,true); step(57); CHECK(keys_get()==KEY_NONE);
    step(1); CHECK(keys_get()==KEY_ACK); key(3,false); step(10);
    key(0,true); step(20); key(1,true); step(20); CHECK(keys_get()==KEY_NONE);
    key(0,false); key(1,false); step(10); CHECK(keys_get()==KEY_ESC); CHECK(keys_get()==KEY_NONE);
    key(2,true); step(3010); key(2,false); step(10); CHECK(keys_get()==KEY_SET_LONG); CHECK(keys_get()==KEY_NONE);
    key(2,true); step(30); key(2,false); step(10); CHECK(keys_get()==KEY_SET);
    key(3,true); step(60); step(501); CHECK(keys_get()==KEY_NONE); key(3,false); step(10);
    key(0,true); step(200); CHECK(keys_get()==KEY_UP); key(1,true); step(200); CHECK(keys_get()==KEY_DOWN);
    key(0,false); key(1,false); step(10); CHECK(keys_get()==KEY_NONE);
    keys_rearm(); key(0,true); step(200); CHECK(keys_get()==KEY_NONE); key(0,false); step(10);
    memset(frame,'X',sizeof frame); gpio_write(board()->reftest,true); lcd_init(); lcd_frame(frame);
    for(i=0;i<100;i++) { lcd_task(); fake_advance(1); }
    CHECK((fake_port(PORT_A)&8)!=0); CHECK((fake_ddr(PORT_A)&4)==0);
    rs485_init(); fake_uart_complete=false; CHECK(rs485_line("P01 BOARD 24 OK")); CHECK(!rs485_line("busy"));
    for(i=0;i<150;i++) rs485_task();
    CHECK((fake_port(PORT_D)&0x80)!=0); fake_uart_complete=true; rs485_task();
    CHECK(strstr(fake_uart_log,"P01 BOARD 24 OK\r\n")!=NULL);
    CHECK((fake_port(PORT_D)&0x80)==0);
    relays_safe(); CHECK(!timer_run_active()); CHECK(!relay_alarm_sense());
    relay_alarm(true); CHECK(relay_alarm_sense()); relays_safe();
    outputs_hw_apply(false,false,0); outputs_hw_apply(true,false,APP_RUN_WINDOW_MS);
    fake_advance(APP_RUN_WINDOW_MS-1u); outputs_hw_apply(true,false,10); CHECK(timer_run_remaining()==1);
    fake_advance(1); outputs_hw_apply(true,false,9); CHECK(!timer_run_active());
    outputs_hw_apply(true,false,APP_RUN_WINDOW_MS); CHECK(!timer_run_active()); CHECK(timer_run_expired());
    timer_run_ack_expiry(); outputs_hw_apply(true,false,APP_RUN_WINDOW_MS); CHECK(timer_run_active()); outputs_hw_apply(false,false,0);
    fake_reset(); gpio_init(); keys_init(); step(10); keys_repeat(true);
    key(0,true); step(7); CHECK(keys_held()==0 && keys_get()==KEY_NONE);
    step(1); CHECK((keys_held()&1)!=0); step(149); CHECK(keys_get()==KEY_NONE);
    step(1); CHECK(keys_get()==KEY_UP); step(449); CHECK(keys_get()==KEY_NONE);
    step(1); CHECK(keys_get()==KEY_UP); /* first repeat at 600 ms */
    for(i=0;i<16;i++) { step(149); CHECK(keys_get()==KEY_NONE); step(1); CHECK(keys_get()==KEY_UP); }
    step(49); CHECK(keys_get()==KEY_NONE); step(1); CHECK(keys_get()==KEY_UP); /* 3 s acceleration */
    step(26950); /* 30 s held; drain prior queued repeats before crossing stuck-key threshold */
    for(i=0;i<8;i++) (void)keys_get();
    step(201); CHECK(keys_get()==KEY_NONE);
    key(0,false); step(10); key(0,true); step(200); CHECK(keys_get()==KEY_UP);
    printf("peripherals: %u checks PASS\n",checks);
}
