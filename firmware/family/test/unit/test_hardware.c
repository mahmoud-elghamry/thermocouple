#include "app/timing.h"
#include <stdio.h>
#include <stdlib.h>
#include "board/board_cfg.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "mcal/wdt.h"
#include "mcal/eeprom.h"
#include "mcal/flash_crc.h"
#include "drivers/iso_spi.h"
#include "drivers/ad7124.h"
#include "drivers/tmp126.h"
#include "fake_hw.h"
static unsigned checks;
void test_scan(void);
void test_peripherals(void);
void test_service(void);
void test_main(void);
#define CHECK(x) do { ++checks; if (!(x)) { printf("FAIL %s:%d %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
static void init_bank(uint8_t b) {
    res_t r = RES_BUSY; unsigned i;
    for (i=0;i<1000 && r==RES_BUSY;i++) { r=ad_init(b); fake_advance(1); }
    CHECK(r==RES_OK);
}
static void reset_driver(void) { fake_reset(); gpio_init(); timer_init(); iso_init(); ad_reset_state(); cj_reset(); }
static res_t verify_bank(void) { unsigned i; res_t r=RES_BUSY; for(i=0;i<32 && r==RES_BUSY;i++) r=ad_verify(0); return r; }
static void error_matrix(void) {
    static const uint8_t slots[]={0,13,14,8,9,10,11,12};
    static const uint8_t bank_bits[]={19,18,9,7,6,5,4,3,2,1};
    unsigned s,b;
    for(s=0;s<8;s++) {
        for(b=0;b<10;b++) CHECK(ad_classify_error(slots[s],1UL<<bank_bits[b])==FC_B04_ADC_ERROR);
        for(b=16;b<=17;b++) CHECK(ad_classify_error(slots[s],1UL<<b)==
            (s==0?FC_C02_RANGE:s==1?FC_C03_COMMON_MODE:s==2?FC_C01_OPEN:FC_B04_ADC_ERROR));
        for(b=12;b<=15;b++) CHECK(ad_classify_error(slots[s],1UL<<b)==
            (s==0?FC_C07_OVUV:s==1?FC_C03_COMMON_MODE:s==2?FC_NONE:
             ((slots[s]==10 || slots[s]==11) && b==12)?FC_NONE:FC_B04_ADC_ERROR));
        CHECK(ad_classify_error(slots[s],1UL<<11)==(slots[s]==8?FC_B06_REF:FC_B04_ADC_ERROR));
    }
}
static void driver_faults(void) {
    static const uint8_t ids[]={0x12,0x14,0x16,0x17,0,0xFF,0x11,0x22};
    unsigned i,k; uint32_t code=0; res_t r; int32_t temp;
    for(i=0;i<8;i++) {
        reset_driver(); fake_ad_reg(0,5,ids[i]); r=RES_BUSY;
        for(k=0;k<1500 && r==RES_BUSY;k++) { r=ad_init(0); fake_advance(1); }
        CHECK(i<4?r==RES_OK:r==RES_ERR_ID);
    }
    reset_driver(); init_bank(0); ad_scan_begin(0,1);
    fake_ad_reg(0,0x30,0xA501FE); CHECK(verify_bank()==RES_ERR_READBACK); CHECK(ad_fault(0)==FC_B13_SIGNATURE);
    reset_driver(); init_bank(0); ad_scan_begin(0,0);
    fake_ad_reg(0,0x21,0); CHECK(verify_bank()==RES_ERR_READBACK); CHECK(ad_fault(0)==FC_B03_ADC_READBACK);
    reset_driver(); init_bank(0); ad_scan_begin(0,0); fake_ad_mclk(0,true,false);
    CHECK(ad_start_slot(0,0)==RES_OK); fake_advance(43); CHECK(ad_poll(0,&code)==RES_ERR_READBACK);
    CHECK(ad_fault(0)==FC_B05_ADC_STALLED);
    reset_driver(); init_bank(0); ad_scan_begin(0,0); fake_ad_mclk(0,false,true);
    CHECK(ad_start_slot(0,0)==RES_ERR_READBACK); CHECK(ad_fault(0)==FC_B05_ADC_STALLED);
    reset_driver(); init_bank(0); ad_scan_begin(0,0); CHECK(ad_start_slot(0,0)==RES_OK);
    fake_ad_por(0,true); fake_advance(43); CHECK(ad_poll(0,&code)==RES_ERR_READBACK); CHECK(ad_fault(0)==FC_B15_ADC_RESET);
    reset_driver(); init_bank(0); ad_scan_begin(0,0); CHECK(ad_start_slot(0,0)==RES_OK);
    fake_ad_ready(0,1000); fake_advance(APP_ADC_RDY_MAX_MS); CHECK(ad_poll(0,&code)==RES_ERR_TIMEOUT);
    reset_driver(); init_bank(0); ad_scan_begin(0,0); CHECK(ad_start_slot(0,0)==RES_OK);
    fake_ad_channel(0,1); fake_advance(43); CHECK(ad_poll(0,&code)==RES_ERR_READBACK); CHECK(ad_fault(0)==FC_B05_ADC_STALLED);
    for(i=APP_ADC_RDY_MIN_MS;i<=APP_ADC_RDY_MAX_MS;i+=APP_ADC_RDY_MAX_MS-APP_ADC_RDY_MIN_MS) {
        reset_driver(); init_bank(0); ad_scan_begin(0,0); fake_ad_ready(0,(uint16_t)i);
        CHECK(ad_start_slot(0,0)==RES_OK); fake_advance(i); CHECK(ad_poll(0,&code)==RES_OK);
    }
    reset_driver(); init_bank(0); ad_scan_begin(0,0); CHECK(ad_start_slot(0,0)==RES_OK);
    fake_ad_error(0,1UL<<17); fake_advance(43); CHECK(ad_poll(0,&code)==RES_OK);
    CHECK(ad_fault(0)==FC_C02_RANGE && (ad_errors(0)&(1UL<<17))!=0);
    CHECK(fake_ad_get(0,6)==0); /* clear-on-read must not erase the captured error */
    reset_driver(); CHECK(cj_init(0)==RES_OK); fake_advance(8);
    fake_tmp_reg(0,0,0xEC00); CHECK(cj_read(0,&temp)==RES_OK && temp==-40000);
    fake_tmp_reg(0,0,0x3E80); CHECK(cj_read(0,&temp)==RES_OK && temp==125000);
    fake_tmp_reg(0,0,0xFFFC); CHECK(cj_read(0,&temp)==RES_OK && temp==-32);
    fake_tmp_reg(0,0,0xEBFC); CHECK(cj_read(0,&temp)==RES_ERR_RANGE);
    fake_tmp_reg(0,0,0x3E84); CHECK(cj_read(0,&temp)==RES_ERR_RANGE);
    fake_tmp_reg(0,0,0); fake_tmp_reg(0,2,1); CHECK(cj_read(0,&temp)==RES_OK);
    CHECK(cj_read(0,&temp)==RES_OK); CHECK(cj_read(0,&temp)==RES_OK); CHECK(cj_read(0,&temp)==RES_ERR_RANGE);
    fake_tmp_reg(0,2,0x81); CHECK(cj_read(0,&temp)==RES_ERR_CRC);
    CHECK(fake_bus_errors==0);
}
int main(void) {
    uint32_t code=0; int32_t temp=0; res_t r; unsigned i;
    const uint8_t crcvec[]={0x07,0x47,0xFA,0xFE};
    fake_reset(); gpio_init(); timer_init(); iso_init(); ad_reset_state(); cj_reset();
    CHECK(board()->banks==3 && board()->channels==24);
    CHECK(fake_port(PORT_B)==0x97 && fake_ddr(PORT_B)==0xBF);
    for(i=0;i<board()->key_count;i++) { /* keys have no external pull-up: input with internal pull-up */
        pin_t k=board()->keys[i]; uint8_t m=(uint8_t)(1u<<(k%8u));
        CHECK((board()->ddr_init[k/8u]&m)==0 && (board()->port_init[k/8u]&m)!=0);
    }
    CHECK(iso_select(0)==RES_OK); CHECK(iso_select(1)==RES_BUSY);
    CHECK(iso_sio_write_enable(true)==RES_ERR_RANGE); iso_deselect();
    CHECK(ad_crc8(crcvec,4)==0x90);
    CHECK(flash_crc_bytes((const uint8_t *)"123456789",9)==0x29B1);
    CHECK(ee_write_byte(4096,3)==RES_ERR_RANGE);
    CHECK(ee_write_byte(0xF00,0xA5)==RES_OK && ee_read(0xF00)==0xA5);
    CHECK(!flow_check(3,7,tick_ms())); CHECK(flow_check(7,7,tick_ms()));
    fake_advance(101); CHECK(!flow_check(7,7,0));
    timer_run_start(APP_RUN_WINDOW_MS); fake_advance(APP_RUN_WINDOW_MS-1u); CHECK(timer_run_active());
    fake_advance(1); CHECK(!timer_run_active());
    init_bank(0);
    fake_ad_crc(0,1); CHECK(ad_read(0,5,&code)==RES_OK);
    fake_ad_crc(0,3); CHECK(ad_read(0,5,&code)==RES_ERR_CRC);
    ad_scan_begin(0,0); CHECK(ad_start_slot(0,0)==RES_OK);
    fake_advance(35); CHECK(ad_poll(0,&code)==RES_BUSY);
    fake_advance(8); CHECK(ad_poll(0,&code)==RES_OK && code==0x800000);
    CHECK(ad_slot_image(13,15)==0x41F1); CHECK(ad_slot_image(14,7)==0x11CF);
    CHECK(ad_classify_error(0,1UL<<17)==FC_C02_RANGE);
    CHECK(ad_classify_error(0,1UL<<12)==FC_C07_OVUV);
    CHECK(ad_classify_error(10,1UL<<12)==FC_NONE);
    CHECK(ad_classify_error(11,1UL<<12)==FC_NONE);
    CHECK(ad_classify_error(8,1UL<<11)==FC_B06_REF);
    CHECK(ad_classify_error(14,1UL<<16)==FC_C01_OPEN);
    CHECK(ad_classify_error(9,1UL<<12)==FC_B04_ADC_ERROR);
    CHECK(cj_init(0)==RES_OK); fake_advance(8);
    CHECK(cj_read(0,&temp)==RES_OK && temp==25000); CHECK(cj_last_id(0)==0x2126);
    fake_tmp_reg(0,0,0); CHECK(cj_read(0,&temp)==RES_OK && temp==0);
    fake_tmp_crc(0,1); CHECK(cj_read(0,&temp)==RES_OK);
    fake_tmp_crc(0,2); CHECK(cj_read(0,&temp)==RES_ERR_CRC);
    fake_tmp_reg(0,12,0xFFFF); CHECK(cj_read(0,&temp)==RES_ERR_ID);
    fake_tmp_reg(0,12,0x2126); fake_tmp_reg(0,5,0); CHECK(cj_read(0,&temp)==RES_ERR_READBACK);
    for(i=0;i<2;i++) { fake_reset(); gpio_init(); iso_init(); ad_reset_state();
        init_bank(0); fake_ad_ready(0,i ? APP_ADC_RDY_MAX_MS+1u:APP_ADC_RDY_MIN_MS-1u); ad_scan_begin(0,0);
        CHECK(ad_start_slot(0,0)==RES_OK); fake_advance(i ? APP_ADC_RDY_MAX_MS+1u:APP_ADC_RDY_MIN_MS-1u);
        r=ad_poll(0,&code); CHECK(r!=RES_OK && r!=RES_BUSY);
    }
    error_matrix(); driver_faults();
    printf("hardware: %u checks PASS\n", checks); test_scan(); test_peripherals(); test_service(); test_main(); return 0;
}
