#include "fake_hw.h"
#include "mcal/timer.h"
#include <string.h>
typedef struct {
    uint32_t reg[0x39],code[15],start,error;
    uint16_t ready; uint8_t bad_crc,slot;
    bool crc,converting,por,forced_por,stuck,torn;
} model_t;
static model_t m[MAX_BANKS];
static uint8_t bank,pos,reg,n,frame[8],answer[8];
static bool read_frame;
/* Independent bitwise polynomial reference. */
static uint8_t crc8(const uint8_t *p,uint8_t count) {
    uint16_t c=0; uint8_t i,j;
    for(i=0;i<count;i++) { c^=(uint16_t)p[i]<<8;
        for(j=0;j<8;j++) c=(uint16_t)((c&0x8000u)?(c<<1)^0x0700u:c<<1);
    } return (uint8_t)(c>>8);
}
static void reset_one(uint8_t b) {
    uint8_t i; model_t *d=&m[b]; memset(d,0,sizeof *d);
    d->reg[0]=0x90; d->reg[1]=0; d->reg[5]=0x12; d->reg[7]=0x40;
    for(i=0;i<16;i++) d->reg[9+i]=1;
    for(i=0;i<8;i++) { d->reg[0x19+i]=0x0860; d->reg[0x21+i]=0x060180;
        d->reg[0x29+i]=0x800000; d->reg[0x31+i]=0x500000;
    }
    for(i=0;i<15;i++) d->code[i]=0x800000;
    d->code[8]=0xEAAAAB; d->code[10]=0xA0C49C; d->code[11]=0x810625;
    d->code[12]=0x9C28F6; d->code[13]=0xC00000; d->code[14]=0x853E2D;
    d->ready=43; d->por=true;
}
void fake_ad_reset(void) { uint8_t b; for(b=0;b<MAX_BANKS;b++) reset_one(b); }
void fake_ad_select(uint8_t b) { bank=b; pos=0; n=0; memset(frame,0,sizeof frame); memset(answer,0,sizeof answer); }
static uint8_t status(model_t *d) {
    bool busy=d->converting && tick_ms()-d->start<d->ready;
    return (uint8_t)((busy?0x80:0)|((d->por||d->forced_por)?0x10:0)|(d->error?0x40:0)|d->slot);
}
uint8_t fake_ad_byte(uint8_t byte) {
    model_t *d=&m[bank]; uint32_t v; uint8_t i,w;
    if(pos>=8) { ++fake_bus_errors; return 0xFF; }
    frame[pos]=byte;
    if(pos==0 && byte==0xFF) { ++pos; return 0xFF; }
    if(pos && frame[0]==0xFF) { ++pos; return 0xFF; }
    if(pos==0) {
        reg=byte&63; read_frame=(byte&0x40)!=0;
        if(reg>=0x39) { ++fake_bus_errors; return 0xFF; }
        w=(reg==0 || reg==5 || reg==8)?1:(reg==2?4:((reg==1 || reg==4 || (reg>=9 && reg<=0x20))?2:3));
        n=(uint8_t)(1+w+(d->crc?1:0)); v=d->reg[reg];
        if(reg==0) v=status(d);
        if(reg==2) { v=(d->code[d->slot]<<8)|status(d); d->converting=false; d->reg[1]=0x0748; }
        if(reg==6) { v=d->error; d->error=0; }
        if(reg==8) v=d->stuck?7:(d->torn?++d->reg[8]:(tick_ms()/10)&255u);
        answer[0]=byte;
        for(i=0;i<w;i++) answer[i+1]=(uint8_t)(v>>(8u*(w-i-1)));
        if(d->crc) {
            answer[w+1]=crc8(answer,(uint8_t)(w+1));
            if(read_frame && d->bad_crc) { --d->bad_crc; answer[w+1]^=1; }
        }
    }
    return answer[pos++];
}
void fake_ad_end(void) {
    model_t *d=&m[bank]; uint8_t i,w; uint32_t v=0;
    if(pos==8 && frame[0]==0xFF) {
        uint8_t bad_crc=d->bad_crc; uint16_t ready=d->ready; uint32_t id=d->reg[5];
        bool stuck=d->stuck,torn=d->torn;
        reset_one(bank); d->bad_crc=bad_crc; d->ready=ready; d->reg[5]=id;
        d->stuck=stuck; d->torn=torn; return;
    }
    if(read_frame || pos<2 || pos!=n) return;
    w=(uint8_t)(n-1-(d->crc?1:0));
    if(d->crc && crc8(frame,(uint8_t)(w+1))!=frame[w+1]) { d->error|=4; return; }
    for(i=0;i<w;i++) v=(v<<8)|frame[i+1];
    d->reg[reg]=v;
    if(reg==7) d->crc=(v&4u)!=0;
    if(reg>=9 && reg<=0x17 && (v&0x8000u)) d->slot=(uint8_t)(reg-9);
    if(reg==1) {
        d->por=false;
        if((v&0x3Cu)==4 || (v&0x3Cu)==0x14 || (v&0x3Cu)==0x18) {
            d->start=tick_ms(); d->converting=true;
        }
    }
}
void fake_ad_reg(uint8_t b,uint8_t r,uint32_t v) { m[b].reg[r]=v; }
uint32_t fake_ad_get(uint8_t b,uint8_t r) { return m[b].reg[r]; }
void fake_ad_code(uint8_t b,uint8_t s,uint32_t v) { m[b].code[s]=v; }
void fake_ad_crc(uint8_t b,uint8_t c) { m[b].bad_crc=c; }
void fake_ad_ready(uint8_t b,uint16_t d) { m[b].ready=d; }
void fake_ad_error(uint8_t b,uint32_t e) { m[b].error=e; }
void fake_ad_por(uint8_t b,bool on) { m[b].forced_por=on; }
void fake_ad_channel(uint8_t b,uint8_t s) { m[b].slot=s; }
void fake_ad_mclk(uint8_t b,bool stuck,bool torn) { m[b].stuck=stuck; m[b].torn=torn; }
