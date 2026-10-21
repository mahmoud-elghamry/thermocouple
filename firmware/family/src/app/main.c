#include "app/service.h"
#include "app/protection.h"
#include "app/app.h"
#include "app/ee_owner.h"
#include "app/stack_budget.h"
#include "services/scan.h"
#include "services/fault.h"
#include "drivers/iso_spi.h"
#include "drivers/lcd.h"
#include "drivers/keys.h"
#include "drivers/rs485.h"
#include "drivers/relays.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "mcal/wdt.h"
#include "mcal/eeprom.h"
#include "mcal/flash_crc.h"
#include <string.h>
#ifdef __AVR__
#include <avr/interrupt.h>
#include <avr/io.h>
#define stack_guard ((volatile uint8_t *)(RAMEND-APP_STACK_BYTES))
#else
static uint8_t stack_guard[16];
#endif
typedef enum { BOOT_LCD, BOOT_FLASH, LOAD_SETTINGS_A, LOAD_SETTINGS_B, RELOAD_SETTINGS_A,
               LOAD_CAL_A, LOAD_CAL_B, RELOAD_CAL_A, BEGIN_ACQ, LOOP } boot_t;
static boot_t boot;
static settings_t active;
static calibration_t calibration;
static fault_registry_t faults;
static uint8_t *bytes;
static uint16_t load_pos;
static uint32_t boot_progress,boot_time;
static uint32_t sequence_a;
static bool cal_a_valid;
static bool a_valid,b_valid,set_valid,cal_valid,flash_valid,service_entry;
static uint8_t cal_slot,settings_slot,mode;
static void load_bytes(uint16_t base,uint16_t length) {
    uint8_t i;
    for(i=0;i<16 && load_pos<length;i++,load_pos++) bytes[load_pos]=ee_read((uint16_t)(base+load_pos));
    boot_progress=tick_ms();
}
void f0_init(void) {
    uint8_t guard;
    gpio_init(); relays_safe(); fault_init(&faults); keys_init();
    if(!fuses_ok()) (void)fault_raise(&faults,FC_G15_FUSES,0);
    timer_init();
#ifdef __AVR__
    sei();
#endif
    iso_init(); rs485_init(); lcd_init(); flash_crc_begin();
    for(guard=0;guard<16;guard++) stack_guard[guard]=0xA5;
    memset(&active,0,sizeof active);
    memset(&calibration,0,sizeof calibration);
    boot=BOOT_LCD; mode=START_LATCHED; boot_time=boot_progress=tick_ms();
    a_valid=b_valid=set_valid=cal_valid=flash_valid=service_entry=false;
    cal_slot=settings_slot=2; load_pos=0;
    bytes=ee_owner_boot_image();
}
static void boot_step(void) {
    res_t r; bool av,bv; uint8_t i;
    switch(boot) {
    case BOOT_LCD:
        /* Power-up gestures: ACK+SET reserved for F2 recovery, never an ACK. */
        if(tick_ms()-boot_time>=300) {
            service_entry=(keys_held()&12u)==4u; keys_rearm(); boot=BOOT_FLASH;
        }
        boot_progress=tick_ms(); break;
    case BOOT_FLASH:
        r=flash_crc(); boot_progress=tick_ms();
        if(r!=RES_BUSY) {
            flash_valid=r==RES_OK; if(!flash_valid) (void)fault_raise(&faults,FC_G03_FLASH_CRC,0);
            boot=LOAD_SETTINGS_A; load_pos=0;
        } break;
    case LOAD_SETTINGS_A:
        load_bytes(0x40,SETTINGS_SLOT_SIZE);
        if(load_pos==SETTINGS_SLOT_SIZE) {
            a_valid=set_unpack(bytes,board()->channels,board()->channels,&active)==RES_OK;
            sequence_a=active.sequence;
            boot=LOAD_SETTINGS_B; load_pos=0;
        } break;
    case LOAD_SETTINGS_B:
        load_bytes(0x340,SETTINGS_SLOT_SIZE);
        if(load_pos==SETTINGS_SLOT_SIZE) {
            int selected;
            b_valid=set_unpack(bytes,board()->channels,board()->channels,&active)==RES_OK;
            selected=set_select(a_valid,sequence_a,b_valid,active.sequence); set_valid=selected>=0;
            settings_slot=selected<0?2:(uint8_t)selected;
            if(selected==0) { boot=RELOAD_SETTINGS_A; load_pos=0; break; }
            if(!set_valid) {
                memset(&active,0,sizeof active); active.board_type=board()->channels; active.channel_count=board()->channels;
                (void)fault_raise(&faults,FC_G01_SETTINGS_INVALID,0);
            }
            boot=LOAD_CAL_A; load_pos=0;
        } break;
    case RELOAD_SETTINGS_A:
        load_bytes(0x40,SETTINGS_SLOT_SIZE);
        if(load_pos==SETTINGS_SLOT_SIZE) { set_valid=set_unpack(bytes,board()->channels,board()->channels,&active)==RES_OK; boot=LOAD_CAL_A; load_pos=0; }
        break;
    case LOAD_CAL_A:
        load_bytes(0x640,CAL_SLOT_SIZE);
        if(load_pos==CAL_SLOT_SIZE) {
            cal_a_valid=cal_unpack(bytes,board()->banks,&calibration)==RES_OK; sequence_a=calibration.sequence;
            boot=LOAD_CAL_B; load_pos=0;
        }
        break;
    case LOAD_CAL_B:
        load_bytes(0x740,CAL_SLOT_SIZE);
        if(load_pos==CAL_SLOT_SIZE) {
            int selected;
            av=cal_a_valid; bv=cal_unpack(bytes,board()->banks,&calibration)==RES_OK;
            selected=set_select(av,sequence_a,bv,calibration.sequence);
            if(selected==0) { boot=RELOAD_CAL_A; load_pos=0; break; }
            cal_slot=selected<0?2:(uint8_t)selected;
            if(selected<0) {
                memset(&calibration,0,sizeof calibration); calibration.bank_count=board()->banks;
                for(i=0;i<board()->banks;i++) calibration.ref_ppm[i]=CAL_MISSING;
                for(i=0;i<MAX_CHANNELS;i++) calibration.baseline_nV[i]=CAL_MISSING;
            }
            cal_valid=selected>=0 && set_valid && cal_complete(&calibration,&active);
            if(!cal_valid) (void)fault_raise(&faults,FC_G10_CALIBRATION,0);
            boot=BEGIN_ACQ;
        } break;
    case RELOAD_CAL_A:
        load_bytes(0x640,CAL_SLOT_SIZE);
        if(load_pos==CAL_SLOT_SIZE) {
            cal_slot=0; cal_valid=cal_unpack(bytes,board()->banks,&calibration)==RES_OK && set_valid && cal_complete(&calibration,&active);
            if(!cal_valid) (void)fault_raise(&faults,FC_G10_CALIBRATION,0); boot=BEGIN_ACQ;
        } break;
    case BEGIN_ACQ:
        mode=service_entry?SERVICE:((set_valid && cal_valid)?START_LATCHED:CONFIG_LOCK);
        scan_init(service_entry?NULL:&active,&calibration,&faults);
        if(service_entry) svc_init(&active,&calibration,set_valid,a_valid,b_valid,cal_slot,flash_valid);
        else { char frame[80]; memset(frame,' ',80);
            memcpy(frame,mode==CONFIG_LOCK?"LOCKED: CALIBRATE  ":"START: ACK REQUIRED",19); lcd_frame(frame); }
        ee_owner_init(&active,&calibration,settings_slot,cal_slot,set_valid);
        app_init(&active,&calibration,&faults,set_valid,service_entry);
        keys_rearm(); boot=LOOP; break;
    default: relays_safe(); boot=BEGIN_ACQ; break;
    }
}
void f0_task(void) {
    uint32_t start=tick_ms(),progress; uint8_t seen=0,i;
    if(boot!=LOOP) { boot_step(); progress=boot_progress; }
    else { scan_task(); progress=scan_progress_ms(); }
    seen|=1;
    keys_task(); seen|=2;
    if(boot==LOOP && flash_valid) {
        seen|=(uint8_t)(app_step(tick_ms()-progress<=100u)<<2);
        mode=(uint8_t)app_protection()->mode;
        if(mode==SERVICE) { svc_task(); seen|=8; }
    } else { relays_safe(); seen|=12; }
    lcd_task(); seen|=16; rs485_task(); seen|=32;
    /* SERVICE steps the same EEPROM owner itself (also used by standalone
     * service driver tests). Normal mode executes exactly one owner step here. */
    if(boot==LOOP && mode!=SERVICE && flash_valid) ee_owner_step();
    seen|=64;
    for(i=0;i<16;i++) if(stack_guard[i]!=0xA5) {
        relays_safe(); (void)fault_raise(&faults,FC_G04_INTERNAL,0); return;
    }
    seen|=128;
    if(tick_ms()-start>8) { relays_safe(); (void)fault_raise(&faults,FC_G04_INTERNAL,0); return; }
    if(mode==SERVICE) svc_loop_time((uint16_t)(tick_ms()-start));
    if(boot==LOOP) app_loop_time((uint16_t)(tick_ms()-start));
    (void)flow_check(seen,255,progress);
}
uint8_t f0_mode(void) { return mode; }
#ifndef FAMILY_TEST
int main(void) { f0_init(); for(;;) f0_task(); }
#endif
