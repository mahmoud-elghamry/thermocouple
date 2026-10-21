#include "drivers/tmp126.h"
#include "app/cj_schedule.h"
#include "drivers/iso_spi.h"
#include "board/board_cfg.h"
#include <string.h>
static uint8_t age[10];
static uint16_t last_id[10];
static uint8_t reading,read_step;
static uint16_t sample[5];
uint16_t cj_crc16(const uint8_t *p,uint8_t n) {
    uint16_t c=0xFFFF; uint8_t i,j;
    for(i=0;i<n;i++) { c^=(uint16_t)p[i]<<8; for(j=0;j<8;j++) c=(uint16_t)((c&0x8000u)?(c<<1)^0x1021u:c<<1); }
    return c;
}
void cj_reset(void) { memset(age,0,sizeof age); memset(last_id,0,sizeof last_id); read_step=0; }
uint16_t cj_last_id(uint8_t j) { return j<10?last_id[j]:0; }
static uint16_t signature(uint8_t j) { return (uint16_t)(0xC000u+0x40u*j); }
static res_t frame(uint8_t j,uint16_t cmd,uint16_t *v) {
    uint8_t bytes[4],k; uint16_t dummy,crc; res_t r;
    if(j>=board()->cj_count) return RES_ERR_RANGE;
    for(k=0;k<2;k++) {
        r=iso_select((uint8_t)(ISO_CJ_BASE+j)); if(r!=RES_OK) return r;
        (void)iso_sio_write_enable(true); (void)iso_word(cmd,&dummy);
        if(cmd&0x100u) {
            (void)iso_sio_write_enable(false); (void)iso_word(0xFFFF,v); (void)iso_word(0xFFFF,&crc);
        } else {
            (void)iso_word(*v,&dummy); crc=0;
            if(cmd&0x4000u) {
                bytes[0]=(uint8_t)(cmd>>8); bytes[1]=(uint8_t)cmd;
                bytes[2]=(uint8_t)(*v>>8); bytes[3]=(uint8_t)*v;
                (void)iso_word(cj_crc16(bytes,4),&dummy);
            }
        }
        iso_deselect();
        if(!(cmd&0x100u)) return RES_OK;
        bytes[0]=(uint8_t)(cmd>>8); bytes[1]=(uint8_t)cmd; bytes[2]=(uint8_t)(*v>>8); bytes[3]=(uint8_t)*v;
        if(cj_crc16(bytes,4)==crc) return RES_OK;
    }
    return RES_ERR_CRC;
}
res_t cj_init(uint8_t j) {
    uint16_t v=4; res_t r=frame(j,0x0003,&v); /* OPEN-Q12: configuration write without CRC */
    if(r==RES_OK) r=frame(j,0x4503,&v);
    if(r!=RES_OK) return r; if(v!=4) return RES_ERR_READBACK;
    v=signature(j); r=frame(j,0x4405,&v);
    if(r==RES_OK) r=frame(j,0x4505,&v);
    if(r!=RES_OK) return r;
    age[j]=0; return v==signature(j)?RES_OK:RES_ERR_READBACK;
}
res_t cj_read(uint8_t j,int32_t *t) {
    uint8_t i; res_t r=RES_BUSY;
    read_step=0;
    for(i=0;i<5 && r==RES_BUSY;i++) r=cj_read_step(j,t);
    return r;
}
res_t cj_read_step(uint8_t j,int32_t *t) {
    static const uint8_t reg[5]={2,0,12,3,5}; res_t r;
    if(j>=board()->cj_count) return RES_ERR_RANGE;
    if(!read_step || reading!=j) { reading=j; read_step=0; last_id[j]=0; }
    r=frame(j,(uint16_t)(0x4500u|reg[read_step]),&sample[read_step]);
    if(r!=RES_OK) { read_step=0; return r; }
    if(read_step==0) {
        if(sample[0]&0x80u) return RES_ERR_CRC;
        if(sample[0]&1u) age[j]=0; else if(age[j]<255) ++age[j];
    }
    if(read_step==2) last_id[j]=sample[2];
    if(++read_step<5) return RES_BUSY;
    read_step=0;
    if(sample[2]!=0x2126) return RES_ERR_ID;
    if(sample[3]!=4 || sample[4]!=signature(j)) return RES_ERR_READBACK;
    { int32_t scaled=(int32_t)(int16_t)sample[1]*125;
      *t=scaled>=0?scaled/16:-((-scaled+15)/16); /* exact arithmetic >>4, portable for negatives */
    }
    if(age[j]>2 || *t < -40000 || *t>125000 || (sample[1]&3)) return RES_ERR_RANGE;
    return RES_OK;
}
