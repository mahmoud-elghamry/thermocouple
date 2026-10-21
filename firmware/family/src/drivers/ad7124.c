#include "drivers/ad7124.h"
#include "app/acquisition_budget.h"
#include "drivers/iso_spi.h"
#include "board/board_cfg.h"
#include "mcal/timer.h"
#include <string.h>
typedef struct {
    uint32_t offset[6],gain[6],factory,started,scan,errors;
    uint8_t state,index,attempt,slot,mclk,id,verify_index;
    bool crc,active,ready; uint8_t ready_status; uint16_t ready_dt; fault_code_t fault;
} adc_t;
static adc_t a[MAX_BANKS];
static const uint16_t configs[8]={0x0875,0x0A75,0x0840,0x0810,0x0818,0x0810,0x0860,0x0860};
static uint8_t width(uint8_t r) {
    if(r==0 || r==5 || r==8) return 1;
    if(r==2) return 4; /* DATA + appended STATUS */
    if(r==1 || r==4 || (r>=9 && r<=0x20)) return 2;
    return 3;
}
#ifdef __AVR__
#include <avr/pgmspace.h>
#define CRC_MEMORY PROGMEM
#define CRC_BYTE(i) pgm_read_byte(&crc_table[i])
#else
#define CRC_MEMORY
#define CRC_BYTE(i) crc_table[i]
#endif
static const uint8_t crc_table[16] CRC_MEMORY={0,7,14,9,28,27,18,21,56,63,54,49,36,35,42,45};
uint8_t ad_crc8(const uint8_t *p,uint8_t n) {
    uint8_t c=0,i;
    for(i=0;i<n;i++) {
        c^=p[i]; c=(uint8_t)((c<<4)^CRC_BYTE(c>>4));
        c=(uint8_t)((c<<4)^CRC_BYTE(c>>4));
    }
    return c;
}
static res_t transfer(uint8_t b,uint8_t reg,uint32_t *v,bool rd) {
    uint8_t tx[6],rx[6],n,w,i,k; res_t r;
    if(b>=board()->banks || reg>0x38) return RES_ERR_RANGE;
    w=width(reg); n=(uint8_t)(1+w+(a[b].crc?1:0));
    tx[0]=(uint8_t)(reg|(rd?0x40:0));
    for(i=0;i<w;i++) tx[i+1]=rd?0:(uint8_t)(*v>>(8u*(w-1u-i)));
    if(a[b].crc) tx[w+1]=ad_crc8(tx,(uint8_t)(w+1));
    for(k=0;k<3;k++) {
        memcpy(rx,tx,n); r=iso_select(b); if(r!=RES_OK) return r;
        r=iso_xfer(rx,n); iso_deselect(); if(r!=RES_OK) return r;
        rx[0]=tx[0];
        if(rd && a[b].crc && ad_crc8(rx,(uint8_t)(w+1))!=rx[w+1]) continue;
        if(rd) { *v=0; for(i=0;i<w;i++) *v=(*v<<8)|rx[i+1]; }
        return RES_OK;
    }
    a[b].fault=FC_B02_ADC_CRC; return RES_ERR_CRC;
}
res_t ad_read(uint8_t b,uint8_t r,uint32_t *v) { return transfer(b,r,v,true); }
res_t ad_write(uint8_t b,uint8_t r,uint32_t v) { return transfer(b,r,&v,false); }
uint16_t ad_slot_image(uint8_t s,uint32_t n) {
    if(s<8) return (uint16_t)((2u*s<<5)|(2u*s+1u));
    switch(s) {
    case 8:return 0x2251; case 9:return 0x0021; case 10:return 0x039D;
    case 11:return 0x539D; case 12:return 0x3295;
    case 13:return (uint16_t)(0x4011u|((n%16u)<<5));
    case 14:return (uint16_t)(0x1000u|ad_slot_image((uint8_t)(n%8u),n));
    default:return 0x0001;
    }
}
/* Complete static image. OPEN-Q1: filter FS; OPEN-Q7: mux/buffer images. */
static bool image(uint8_t b,uint8_t idx,uint8_t *reg,uint32_t *v) {
    if(idx==0) { *reg=3; *v=0; }
    else if(idx==1) { *reg=4; *v=0; }
    else if(idx==2) { *reg=7; *v=0x47FAFE; }
    else if(idx<11) { *reg=(uint8_t)(0x19+idx-3); *v=configs[idx-3]; }
    else if(idx<19) { *reg=(uint8_t)(0x21+idx-11); *v=idx<17?0xE60180:0x060180; }
    else if(idx<25) { *reg=(uint8_t)(0x29+idx-19); *v=a[b].offset[idx-19]; }
    else if(idx<31) { *reg=(uint8_t)(0x31+idx-25); *v=a[b].gain[idx-25]; }
    else if(idx==31) { *reg=0x30; *v=0xA50000UL|((uint32_t)b<<8)|(0xFFu-b); }
    else return false;
    return true;
}
void ad_reset_state(void) { memset(a,0,sizeof a); }
static bool id_ok(uint32_t id) {
    uint8_t rev=(uint8_t)(id&15u); /* OPEN-Q5: shipping revision whitelist */
    return (id&0xF0u)==0x10u && (rev==2 || rev==4 || rev==6 || rev==7);
}
static res_t init_fail(uint8_t b,res_t r,fault_code_t f) {
    a[b].fault=f;
    if(++a[b].attempt<3) { a[b].state=0; return RES_BUSY; }
    a[b].state=0xFF; return r;
}
static res_t cal_poll(uint8_t b) {
    uint32_t v,e; res_t r=ad_read(b,0,&v);
    if(r!=RES_OK) return r;
    if(v&0x10) return RES_ERR_READBACK;
    if(v&0x80) return tick_ms()-a[b].started>=200?RES_ERR_TIMEOUT:RES_BUSY;
    r=ad_read(b,6,&e); a[b].errors|=e;
    if(r!=RES_OK) return r;
    return e?RES_ERR_READBACK:RES_OK;
}
res_t ad_init(uint8_t b) {
    adc_t *d; res_t r=RES_OK; uint32_t v=0,expected; uint8_t reg,i;
    if(b>=board()->banks) return RES_ERR_RANGE;
    d=&a[b];
    switch(d->state) {
    case 0: {
        uint8_t reset[8]; memset(reset,0xFF,sizeof reset); d->crc=false; d->active=false;
        r=iso_select(b); if(r==RES_OK) { r=iso_xfer(reset,8); iso_deselect(); }
        if(r!=RES_OK) return init_fail(b,r,FC_B01_ADC_ID);
        d->started=tick_ms(); d->state=1; return RES_BUSY;
    }
    case 1:
        if(tick_ms()-d->started<2) return RES_BUSY; /* OPEN-Q3 */
        r=ad_read(b,0,&v); if(r!=RES_OK || !(v&0x10)) return init_fail(b,RES_ERR_ID,FC_B01_ADC_ID);
        r=ad_read(b,5,&v); if(r!=RES_OK || !id_ok(v)) return init_fail(b,RES_ERR_ID,FC_B01_ADC_ID);
        d->id=(uint8_t)v; r=ad_write(b,7,0x47FAFE); d->crc=true;
        if(r==RES_OK) r=ad_read(b,7,&v);
        if(r!=RES_OK || v!=0x47FAFE) return init_fail(b,RES_ERR_READBACK,FC_B03_ADC_READBACK);
        r=ad_write(b,1,0x0748); d->index=0; d->state=2; break;
    case 2:
        /* Do not overwrite factory gains. OFFSETs reset to their documented reset image. */
        if(d->index<19) { (void)image(b,d->index,&reg,&expected); r=ad_write(b,reg,expected);
            if(r==RES_OK) r=ad_read(b,reg,&v);
            if(r!=RES_OK || v!=expected) return init_fail(b,RES_ERR_READBACK,FC_B03_ADC_READBACK);
        } else if(d->index<35) {
            reg=(uint8_t)(9+d->index-19); expected=ad_slot_image((uint8_t)(d->index-19),0);
            r=ad_write(b,reg,expected); if(r==RES_OK) r=ad_read(b,reg,&v);
            if(r!=RES_OK || v!=expected) return init_fail(b,RES_ERR_READBACK,FC_B03_ADC_READBACK);
        } else {
            for(i=0;i<6;i++) {
                r=ad_read(b,(uint8_t)(0x31+i),&d->gain[i]); if(r!=RES_OK) break;
                d->offset[i]=0x800000;
            }
            if(r!=RES_OK) break;
            d->factory=d->gain[0]; (void)image(b,31,&reg,&expected);
            r=ad_write(b,reg,expected); if(r==RES_OK) r=ad_read(b,reg,&v);
            if(r!=RES_OK || v!=expected) return init_fail(b,RES_ERR_READBACK,FC_B13_SIGNATURE);
            r=ad_read(b,6,&v); if(r!=RES_OK || v) return init_fail(b,RES_ERR_READBACK,FC_B04_ADC_ERROR);
            d->state=3;
        }
        ++d->index; break;
    case 3:
        r=ad_write(b,9,0x8001); if(r==RES_OK) r=ad_write(b,0x29,0x800000);
        if(r==RES_OK) r=ad_write(b,1,0x0758); /* OPEN-Q6: full then zero, 200 ms bound */
        d->started=tick_ms(); d->state=4; break;
    case 4:
        r=cal_poll(b); if(r==RES_BUSY) return r;
        if(r!=RES_OK) return init_fail(b,r,FC_B04_ADC_ERROR);
        r=ad_write(b,1,0x0754); d->started=tick_ms(); d->state=5; break;
    case 5:
        r=cal_poll(b); if(r==RES_BUSY) return r;
        if(r!=RES_OK) return init_fail(b,r,FC_B04_ADC_ERROR);
        r=ad_write(b,1,0x0748); if(r==RES_OK) r=ad_read(b,0x29,&d->offset[0]);
        if(r==RES_OK) r=ad_read(b,0x31,&d->gain[0]);
        if(r!=RES_OK) break;
        /* OPEN-Q6: calibration sanity +/-65536 offset, +/-2% factory gain. */
        if(d->offset[0]<0x7F0000 || d->offset[0]>0x810000 || d->factory==0 ||
           (uint64_t)d->gain[0]*100u<(uint64_t)d->factory*98u ||
           (uint64_t)d->gain[0]*100u>(uint64_t)d->factory*102u)
            return init_fail(b,RES_ERR_RANGE,FC_B04_ADC_ERROR);
        d->offset[1]=d->offset[0]; d->gain[1]=d->gain[0];
        r=ad_write(b,0x2A,d->offset[1]); if(r==RES_OK) r=ad_write(b,0x32,d->gain[1]);
        if(r==RES_OK) r=ad_write(b,9,1);
        d->state=6; d->verify_index=0; d->index=0; break;
    case 6:
        if(d->verify_index<32) {
            r=ad_verify(b);
            if(r==RES_OK || r==RES_BUSY) return RES_BUSY;
        } else r=ad_verify_mutable_part(b,d->index++);
        if(r!=RES_OK) return init_fail(b,r,FC_B03_ADC_READBACK);
        if(d->index<19) return RES_BUSY;
        d->fault=FC_NONE; d->state=7; return RES_OK;
    case 7:return RES_OK;
    default:return RES_ERR_READBACK;
    }
    if(r!=RES_OK) return init_fail(b,r,FC_B03_ADC_READBACK);
    return RES_BUSY;
}
res_t ad_verify(uint8_t b) {
    uint8_t reg; uint32_t expected,v=0; res_t r;
    if(b>=board()->banks) return RES_ERR_RANGE;
    if(!image(b,a[b].verify_index,&reg,&expected)) return RES_OK;
    r=ad_read(b,reg,&v); if(r!=RES_OK) return r;
    if(v!=expected) { a[b].fault=reg==0x30?FC_B13_SIGNATURE:FC_B03_ADC_READBACK; return RES_ERR_READBACK; }
    ++a[b].verify_index; return a[b].verify_index==32?RES_OK:RES_BUSY;
}
res_t ad_verify_mutable(uint8_t b) {
    uint8_t i; res_t r;
    for(i=0;i<19;i++) { r=ad_verify_mutable_part(b,i); if(r!=RES_OK) return r; }
    return RES_OK;
}
res_t ad_verify_mutable_part(uint8_t b,uint8_t i) {
    uint32_t v=0; res_t r; uint8_t reg;
    if(b>=board()->banks) return RES_ERR_RANGE;
    if(i>=19) return RES_ERR_RANGE;
    reg=i==0?1:i<17?(uint8_t)(8+i):i==17?5:6;
    r=ad_read(b,reg,&v); if(r!=RES_OK) return r;
    if(i==17) { if(id_ok(v)) return RES_OK; a[b].fault=FC_B01_ADC_ID; return RES_ERR_ID; }
    else if(i==18) { if(!v) return RES_OK; a[b].fault=FC_B04_ADC_ERROR; }
    else { if(v==(i==0?0x0748u:ad_slot_image((uint8_t)(i-1u),a[b].scan))) return RES_OK;
        a[b].fault=FC_B03_ADC_READBACK; }
    return RES_ERR_READBACK;
}
static res_t mclk(uint8_t b,uint8_t *v) {
    uint8_t i; uint32_t prev=0,now=0; res_t r=ad_read(b,8,&prev);
    if(r!=RES_OK) return r;
    for(i=1;i<4;i++) { r=ad_read(b,8,&now); if(r!=RES_OK) return r;
        if(now==prev) { *v=(uint8_t)now; return RES_OK; } prev=now;
    }
    a[b].fault=FC_B05_ADC_STALLED; return RES_ERR_READBACK; /* OPEN-Q11 */
}
void ad_scan_begin(uint8_t b,uint32_t n) {
    if(b<board()->banks) { a[b].scan=n; a[b].fault=FC_NONE; a[b].errors=0; a[b].verify_index=0;
        if(ad_write(b,0x16,ad_slot_image(13,n))!=RES_OK || ad_write(b,0x17,ad_slot_image(14,n))!=RES_OK)
            a[b].fault=FC_B03_ADC_READBACK;
    }
}
res_t ad_start_slot(uint8_t b,uint8_t s) {
    res_t r; if(b>=board()->banks || s>14) return RES_ERR_RANGE;
    if(a[b].active) return RES_BUSY;
    a[b].slot=s; a[b].errors=0; a[b].fault=FC_NONE;
    if(s==0) { r=mclk(b,&a[b].mclk); if(r!=RES_OK) return r; }
    r=ad_write(b,(uint8_t)(9+s),ad_slot_image(s,a[b].scan)|0x8000u);
    if(r==RES_OK) r=ad_write(b,1,0x0744);
    if(r==RES_OK) { a[b].started=tick_ms(); a[b].active=true; a[b].ready=false; }
    return r;
}
fault_code_t ad_classify_error(uint8_t s,uint32_t e) {
    if(s==10 || s==11) e&=~(1UL<<12); /* internal 20mV AINM_UV exception */
    if(s==14) e&=~0xF000UL;
    if(e&~0x3F800UL) return FC_B04_ADC_ERROR;
    if(e&0x800u) return s==8?FC_B06_REF:FC_B04_ADC_ERROR;
    if(e&0x30000UL) return s<8?FC_C02_RANGE:s==14?FC_C01_OPEN:s==13?FC_C03_COMMON_MODE:FC_B04_ADC_ERROR;
    if(e&0xF000u) return s<8?FC_C07_OVUV:s==13?FC_C03_COMMON_MODE:FC_B04_ADC_ERROR;
    return FC_NONE;
}
res_t ad_ready(uint8_t b) {
    uint32_t s=0,dt; res_t r;
    if(b>=board()->banks || !a[b].active) return RES_ERR_RANGE;
    if(a[b].ready) return RES_OK;
    r=ad_read(b,0,&s); if(r!=RES_OK) return r;
    if(s&0x10u) { a[b].fault=FC_B15_ADC_RESET; return RES_ERR_READBACK; }
    dt=tick_ms()-a[b].started;
    if(s&0x80u) { if(dt<57) return RES_BUSY; a[b].fault=FC_B05_ADC_STALLED; return RES_ERR_TIMEOUT; }
    if(dt<36 || dt>57) { a[b].fault=FC_B05_ADC_STALLED; return RES_ERR_TIMEOUT; }
    a[b].ready=true; a[b].ready_status=(uint8_t)s; a[b].ready_dt=(uint16_t)dt;
    return RES_OK;
}
res_t ad_poll(uint8_t b,uint32_t *code) {
    uint32_t s,data=0,e=0; uint8_t clock,k; res_t r=ad_ready(b); fault_code_t f;
    if(r!=RES_OK) return r;
    s=a[b].ready_status;
    /* ad_ready stamped the first observed RDY time (P3). Reading held DATA
     * in a later pass cannot change that observation or its timing check. */
    for(k=0;k<3;k++) {
        r=ad_read(b,2,&data); if(r!=RES_OK) return r;
        if(data&0x10) { a[b].fault=FC_B15_ADC_RESET; return RES_ERR_READBACK; }
        if((data&15)!=a[b].slot || (data&0x80)) { a[b].fault=FC_B05_ADC_STALLED; return RES_ERR_READBACK; }
        if((s|data)&0x40) { /* OPEN-Q4: preserve first error even for clear-on-read bits. */
            r=ad_read(b,6,&e); if(r!=RES_OK) return r; a[b].errors|=e;
        }
        if(!(e&0x7Cu)) break; /* retry communication faults; preserve conversion bits */
    }
    if(k==3) { a[b].fault=FC_B04_ADC_ERROR; return RES_ERR_READBACK; }
    f=ad_classify_error(a[b].slot,a[b].errors&~0x7CUL);
    if(f!=FC_NONE) a[b].fault=f;
    if(a[b].slot==0) { r=mclk(b,&clock); if(r!=RES_OK) return r;
        if(clock==a[b].mclk) { a[b].fault=FC_B05_ADC_STALLED; return RES_ERR_READBACK; }
    }
    r=ad_write(b,(uint8_t)(9+a[b].slot),ad_slot_image(a[b].slot,a[b].scan));
    a[b].active=false; if(r!=RES_OK) return r;
    *code=data>>8; return RES_OK;
}
fault_code_t ad_fault(uint8_t b) { return b<board()->banks?a[b].fault:FC_B04_ADC_ERROR; }
uint32_t ad_errors(uint8_t b) { return b<board()->banks?a[b].errors:0xFFFFFFFFUL; }
uint8_t ad_id(uint8_t b) { return b<board()->banks?a[b].id:0; }
