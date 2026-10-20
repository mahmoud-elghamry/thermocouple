#include "app/service.h"
#include "app/ee_owner.h"
#include "services/scan.h"
#include "services/tc_math.h"
#include "drivers/keys.h"
#include "drivers/lcd.h"
#include "drivers/relays.h"
#include "drivers/rs485.h"
#include "drivers/ad7124.h"
#include "drivers/tmp126.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "mcal/wdt.h"
#include "mcal/eeprom.h"
#include "mcal/flash_crc.h"
#include <stdio.h>
#include <string.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
/* Report format strings stay in flash, rather than consuming the SRAM budget. */
#define snprintf(out,size,fmt,...) snprintf_P((out),(size),PSTR(fmt),__VA_ARGS__)
#endif
#ifndef FAMILY_BUILD_HASH
#define FAMILY_BUILD_HASH "local"
#endif
typedef enum { PASSIVE, PROMPT, CONFIRM, ACTIVE, RELEASE, CAL_COLLECT, CAL_SAVE, FINISH, FINISHED } state_t;
static state_t state;
static const settings_t *settings;
static calibration_t *active_cal,candidate;
static bool settings_good,a_good,b_good,flash_good,test_ok,cal_submitted;
static uint8_t cal_slot,pstep,item,astep,key_index,cal_count;
static uint16_t n_ok,n_fail,worst,ee_index,drop_ms;
static uint32_t started,progress,last_scan,confirmed;
static int32_t sums[24]; /* F0 scope: 24 inputs; 16 REF or 8 burnout sums fit int32. */
static char line[124];
static uint16_t protected_crc;
uint8_t *svc_boot_image(void) { return ee_owner_boot_image(); }
static void display(const char *s) {
    char frame[80]; size_t n=strlen(s); memset(frame,' ',80);
    (void)snprintf(frame,21,"SERVICE MODE %c%02u",astep?'A':'P',astep?astep:pstep);
    if(n>60) n=60; memcpy(frame+20,s,n); lcd_frame(frame);
}
static void report(const char *name,long value,bool ok,const char *reason) {
    (void)snprintf(line,sizeof line,"%c%02u %s %ld %s %s",astep?'A':'P',astep?astep:pstep,name,value,ok?"OK":"FAIL",reason);
    display(line); (void)rs485_line(line); if(ok) ++n_ok; else ++n_fail;
}
static void send_detail(bool ok) {
    display(line); (void)rs485_line(line); if(ok) ++n_ok; else ++n_fail;
}
static uint32_t ee_sequence(uint16_t base) {
    uint8_t i; uint32_t n=0;
    for(i=0;i<4;i++) n|=(uint32_t)ee_read((uint16_t)(base+4+i))<<(8*i);
    return n;
}
static void connected_page(uint8_t page) {
    char frame[80]; uint8_t c,p=20;
    memset(frame,' ',80); memcpy(frame,"SERVICE MODE A07",16);
    for(c=(uint8_t)(12*page);c<12*(page+1) && c<board()->channels;c++) if(confirmed&(1UL<<c)) {
        frame[p++]=(char)('0'+(c+1)/10); frame[p++]=(char)('0'+(c+1)%10); frame[p++]=' ';
    }
    memcpy(frame+60,"UP/DN PAGE SET=YES",18); lcd_frame(frame);
}
void svc_init(const settings_t *cfg,calibration_t *cal,bool valid,bool av,bool bv,uint8_t slot,bool flash) {
    settings=cfg; active_cal=cal; settings_good=valid; a_good=av; b_good=bv;
    cal_slot=slot; flash_good=flash; state=PASSIVE; pstep=1; astep=item=key_index=0;
    n_ok=n_fail=worst=0; started=progress=tick_ms(); confirmed=0; last_scan=0; relays_safe(); keys_rearm();
    ee_owner_init(NULL,cal,2,slot,valid);
}
bool svc_finished(void) { return state==FINISHED; }
uint8_t svc_active_step(void) { return astep; }
uint32_t svc_progress_ms(void) { return progress; }
void svc_loop_time(uint16_t ms) { if(ms>worst) worst=ms; }
void svc_settings_committed(bool valid) { settings_good=valid; }
static void next_active(void) {
    relays_safe(); keys_rearm(); item=0;
    if(++astep>7) { state=FINISH; astep=0; } else state=PROMPT;
}
static void passive(void) {
    const scan_out_t *s=scan_last(); const scan_diag_t *d=scan_diagnostics();
    char name[17]; uint8_t count=1; bool ok=true; long value=0;
    uint8_t f[3]; uint32_t raw;
    /* A complete rotation is needed before reporting each channel's burnout. */
    if(pstep>=6 && s->scan_no==0 && (d->initialized || tick_ms()-started<500)) return;
    if(pstep==13 && d->initialized && s->scan_no<8) return;
    switch(pstep) {
    case 1:
        (void)snprintf(line,sizeof line,"P01 BOARD %u v0.1.0 %s OK",board()->channels,FAMILY_BUILD_HASH);
        display(line); (void)rs485_line(line); ++n_ok; ++pstep; return;
    case 2:
        fuses_read(f); (void)snprintf(line,sizeof line,"P02 FUSES %02X-%02X-%02X %s",f[0],f[1],f[2],fuses_ok()?"OK":"FAIL");
        display(line); (void)rs485_line(line); if(fuses_ok()) ++n_ok; else ++n_fail; ++pstep; return;
    case 3:strcpy(name,"RESET");value=reset_cause();break;
    case 4:strcpy(name,"FLASH_CRC");ok=flash_good;value=flash_crc_value();break;
    case 5:
        count=3; strcpy(name,item==0?"EEPROM_A":item==1?"EEPROM_B":"CAL");
        value=(long)ee_sequence(item==0?0x40:item==1?0x340:cal_slot==1?0x740:0x640);
        (void)snprintf(line,sizeof line,"P05 %s %s seq=%lu OK",name,
            (item==0?a_good:item==1?b_good:(cal_slot<2))?"VALID":"INVALID",(unsigned long)value);
        send_detail(true); if(++item==count) { item=0; ++pstep; } return;
    case 6:count=board()->banks; (void)snprintf(name,sizeof name,"ADC%c_ID",'A'+item);value=ad_id(item);
        ok=value==0x12 || value==0x14 || value==0x16 || value==0x17;break;
    case 7:count=board()->banks; (void)snprintf(name,sizeof name,"ADC%c_REGS",'A'+item);ok=d->registers_ok[item];break;
    case 8:count=board()->banks; (void)snprintf(name,sizeof name,"ADC%c_AVDD",'A'+item);
        raw=d->raw[item][12]; value=(long)((int64_t)scan_emf(raw,1)*6/1000000); ok=scan_limit(12,raw,0,0,0,0)==FC_NONE;break;
    case 9:count=board()->banks; (void)snprintf(name,sizeof name,"ADC%c_REF",'A'+item);
        raw=d->raw[item][8]; value=(long)(((int64_t)((int32_t)raw-0x800000L)*1000000/6990507)-1000000);
        ok=value>=-10000 && value<=10000;break;
    case 10:count=(uint8_t)(2*board()->banks); (void)snprintf(name,sizeof name,"ADC%c_%s",'A'+item/2,item%2?"GAIN":"ZERO");
        raw=d->raw[item/2][item%2?11:9]; value=(long)(scan_emf(raw,item%2?1:32)/1000);
        if(item%2 && value>0) value=(long)((int64_t)scan_emf(d->raw[item/2][10],32)*1000/value);
        ok=scan_limit(item%2?11:9,raw,d->raw[item/2][10],0,0,0)==FC_NONE;break;
    case 11:count=board()->cj_count; (void)snprintf(name,sizeof name,"CJ%u",item+1);value=s->cj_dC[item/2][item%2];
        ok=d->cj_status[item]==RES_OK && value>=0 && value<=700;
        (void)snprintf(line,sizeof line,"P11 %s %04X %lddC %s",name,cj_last_id(item),value,ok?"OK":"FAIL");
        send_detail(ok); if(++item==count) { item=0; ++pstep; } return;
    case 12: {
        temp_dC_t temp=TEMP_DC_INVALID; uint8_t flags;
        int32_t cj=s->cj_dC[item/8][0]+(int32_t)(s->cj_dC[item/8][1]-s->cj_dC[item/8][0])*board()->channel[item].cj_weight_q8/256;
        count=board()->channels; raw=d->raw[item/8][item%8]; value=scan_emf(raw,32)/1000;
        flags=tc_convert(CH_TYPE_K,scan_emf(raw,32),(temp_dC_t)cj,&temp);
        ok=(flags&MEAS_VALID)!=0 && scan_limit(0,raw,0,0,0,0)==FC_NONE &&
            d->cj_status[2*(item/8)]==RES_OK && d->cj_status[2*(item/8)+1]==RES_OK &&
            s->scan_no!=0 && s->meas[item].scan_no==s->scan_no && d->cal_safe[item/8];
        (void)snprintf(line,sizeof line,"P12 CH%02u %lduV %ddC K %s %s",item+1,value,temp,
            (ok || !settings_good || settings->ch[item].type==CH_TYPE_OFF)?"OK":"FAIL",ok?"":"OPEN_OR_INVALID");
        send_detail(ok || !settings_good || settings->ch[item].type==CH_TYPE_OFF);
        if(++item==count) { item=0; ++pstep; } return;
    }
    case 13:count=board()->channels; (void)snprintf(name,sizeof name,"CH%02u_BURN",item+1);value=d->burnout_nV[item];
        ok=(value>=1500000 && value<=10000000) || !settings_good || settings->ch[item].type==CH_TYPE_OFF;break;
    case 14:strcpy(name,"ENGREF");value=gpio_read(board()->refok);ok=value==0 && d->ref_test_ok;break;
    case 15:strcpy(name,"SCAN");value=d->duration_ms;ok=value<=750;break;
    case 16:strcpy(name,"LOOP");value=worst;ok=value<=8;break;
    default:astep=1;state=PROMPT;keys_rearm();return;
    }
    report(name,value,ok,ok?"":"CHECK");
    if(++item==count) { item=0; ++pstep; }
}
static uint16_t record_crc(void) {
    uint16_t a,c=0xFFFF; uint8_t bit;
    /* Includes settings and calibration A/B; scratch is deliberately excluded. */
    for(a=0x40;a<0x840;a++) {
        c^=(uint16_t)ee_read(a)<<8;
        for(bit=0;bit<8;bit++) c=(uint16_t)((c&0x8000u)?(c<<1)^0x1021u:c<<1);
    }
    return c;
}
static void cal_start(void) {
    uint8_t c;
    if(active_cal && cal_validate(active_cal)==RES_OK) candidate=*active_cal;
    else {
        memset(&candidate,0,sizeof candidate); candidate.bank_count=board()->banks;
        for(c=0;c<board()->banks;c++) candidate.ref_ppm[c]=CAL_MISSING;
        for(c=0;c<MAX_CHANNELS;c++) candidate.baseline_nV[c]=CAL_MISSING;
    }
    if(astep==7) {
        for(c=0;c<board()->banks;c++) if(candidate.ref_ppm[c]==CAL_MISSING) {
            report("LEARN_BURNOUT",0,false,"CAL_REF_FIRST"); next_active(); return;
        }
    }
    memset(sums,0,sizeof sums); cal_count=0; last_scan=scan_last()->scan_no; state=CAL_COLLECT;
}
static void collect_cal(void) {
    uint8_t c; const scan_diag_t *d=scan_diagnostics(); const scan_out_t *s=scan_last();
    if(s->scan_no==last_scan) return; last_scan=s->scan_no;
    for(c=0;c<(astep==6?board()->banks:board()->channels);c++) {
        uint8_t bank=astep==6?c:(uint8_t)(c/8);
        if(!d->cal_safe[bank]) {
            report("CALIBRATION",bank,false,"INVALID_SCAN"); next_active(); return;
        }
        if(astep==6) sums[c]+=(int32_t)d->raw[c][8]-0x800000L;
        else if(confirmed&(1UL<<c)) {
            if(s->scan_no%8u!=c%8u) continue;
            sums[c]+=d->burnout_nV[c];
        }
    }
    /* Sixteen REF scans; eight complete rotations (64 scans) give 8 deltas/channel. */
    if(++cal_count<(astep==6?16:64)) return;
    test_ok=true;
    for(c=0;c<(astep==6?board()->banks:board()->channels);c++) {
        if(astep==6) {
            int32_t ppm=(int32_t)(((int64_t)sums[c]/16)*1000000/6990507)-1000000;
            if(ppm < -10000 || ppm>10000) test_ok=false; candidate.ref_ppm[c]=ppm;
        } else if(confirmed&(1UL<<c)) {
            int32_t baseline=(int32_t)(sums[c]/8);
            if(settings_good && settings->ch[c].type==CH_TYPE_OFF) {
                candidate.baseline_nV[c]=CAL_MISSING; candidate.tag[c]=0; continue;
            }
            if(baseline<1500000 || baseline>10000000) test_ok=false;
            candidate.baseline_nV[c]=baseline;
            candidate.tag[c]=settings_good?(uint8_t)((settings->ch[c].type_epoch<<2)|settings->ch[c].type):1;
        }
    }
    if(!test_ok) {
        report("CALIBRATION",0,false,"WINDOW"); next_active(); return;
    }
    cal_submitted=false; state=CAL_SAVE;
}
static void save_cal(void) {
    if(!cal_submitted) {
        res_t r=ee_owner_calibration(&candidate);
        if(r==RES_BUSY) return;
        if(r!=RES_OK) { report("CALIBRATION",0,false,"EEPROM"); next_active(); return; }
        cal_submitted=true;
    } else if(!ee_owner_busy()) {
        if(!ee_owner_cal_saved()) report("CALIBRATION",0,false,"EEPROM");
        else {
            event_t e; memset(&e,0,sizeof e); e.type=EV_CALIBRATION; e.uptime_s=tick_ms()/1000u;
            (void)ee_owner_log(&e);
            report("CALIBRATION",(long)active_cal->sequence,true,"");
        }
        next_active();
    }
}
void svc_task(void) {
    key_t key; uint32_t dt;
    ee_owner_step();
    if(state==FINISHED || rs485_busy()) return;
    key=keys_get(); dt=tick_ms()-started;
    switch(state) {
    case PASSIVE:passive();break;
    case PROMPT:
        (void)snprintf(line,sizeof line,"A%02u DISCONNECT RUN AND ALARM CONTACTS - SET=GO ESC=SKIP",astep);
        display(line); (void)rs485_line(line); keys_rearm(); state=CONFIRM;break;
    case CONFIRM:
        if(key==KEY_ESC) { report("SKIP",0,true,""); next_active(); }
        else if(key==KEY_SET) {
            started=tick_ms(); test_ok=true; item=0; key_index=0; drop_ms=UINT16_MAX; state=ACTIVE;
            if(astep==2) relay_alarm(true);
            if(astep==3) timer_run_start(1000);
            if(astep==4) timer_run_static_high();
            if(astep==5) { protected_crc=record_crc(); ee_index=0; }
            if(astep==6) cal_start();
            if(astep==7) {
                uint8_t c; confirmed=0;
                for(c=0;c<board()->channels;c++) {
                    uint32_t raw=scan_diagnostics()->raw[c/8][c%8];
                    if(raw>167772u && raw<16609444UL) confirmed|=1UL<<c;
                }
                (void)snprintf(line,sizeof line,"A07 CONNECTED_MASK %06lX SET=CONFIRM ESC=SKIP",(unsigned long)confirmed);
                (void)rs485_line(line); item=0; connected_page(item); state=RELEASE; keys_rearm();
            }
        } break;
    case RELEASE:
        if(key==KEY_SET && confirmed) cal_start();
        else if(key==KEY_ESC) { report("SKIP",0,true,""); next_active(); }
        else if(key==KEY_UP || key==KEY_DOWN) { item^=1; connected_page(item); }
        break;
    case ACTIVE:
        if(key!=KEY_NONE && astep!=1) { report("ABORT",0,false,"KEY"); next_active(); break; }
        if(astep==1) {
            static const key_t expected[5]={KEY_UP,KEY_DOWN,KEY_SET,KEY_ACK,KEY_ESC};
            static const char *const names[5]={"UP","DOWN","SET","ACK","UP+DOWN"};
            if(item==0) {
                (void)snprintf(line,sizeof line,"A01 PRESS_%s RELEASE",names[key_index]); display(line); (void)rs485_line(line);
                item=1; keys_rearm(); break;
            }
            if(key==expected[key_index]) item=2;
            if((item==2 && keys_held()==0) || dt>=10000) {
                report(names[key_index],(long)dt,item==2,item==2?"":"TIMEOUT");
                if(++key_index==5) next_active(); else { item=0; started=tick_ms(); }
            }
        } else if(astep==2 || astep==3 || astep==4) {
            if(dt>=100 && dt<1000) {
                if(astep==2 && !relay_alarm_sense()) test_ok=false;
                if(astep==3 && !relay_run_sense()) test_ok=false;
                if(astep==4 && relay_run_sense()) test_ok=false;
            }
            if(dt>=1000 && item==0) { relays_safe(); item=1; }
            if(item && !relay_run_sense() && drop_ms==UINT16_MAX) drop_ms=(uint16_t)(dt-1000);
            if(item && dt>=1100) {
                test_ok&=!relay_run_sense() && !relay_alarm_sense();
                report(astep==2?"ALARM":astep==3?"RUN":"RUN_STATIC",drop_ms,test_ok,"ms"); next_active();
            }
        } else if(astep==5 && ee_ready()) {
            if(ee_index<256) { uint16_t addr=(uint16_t)(0xF00+ee_index);
                uint8_t v=(uint8_t)(ee_index^0xA5);
                if(item==0) { if(ee_owner_scratch(addr,v)==RES_OK) item=1; }
                else if(item==1) { if(ee_read(addr)!=v) test_ok=false; if(ee_owner_scratch(addr,0xFF)==RES_OK) item=2; }
                else { if(ee_read(addr)!=0xFF) test_ok=false; ++ee_index; item=0; }
            } else { test_ok&=protected_crc==record_crc(); report("EEPROM_SCRATCH",256,test_ok,""); next_active(); }
        }
        break;
    case CAL_COLLECT:collect_cal();break;
    case CAL_SAVE:save_cal();break;
    case FINISH:
        (void)snprintf(line,sizeof line,"END %u OK %u FAIL",n_ok,n_fail); display(line); (void)rs485_line(line); state=FINISHED;break;
    default:relays_safe();state=FINISHED;break;
    }
    progress=tick_ms();
}
