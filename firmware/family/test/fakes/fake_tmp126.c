#include "fake_hw.h"
#include "mcal/timer.h"
#include <string.h>
static uint16_t regs[2u*MAX_BANKS][13];
static uint8_t sensor,pos,frame[6],response[6],bad[2u*MAX_BANKS];
static uint32_t last[2u*MAX_BANKS];
static uint16_t crc16(const uint8_t *p,uint8_t n) {
    uint32_t c=0xFFFF; uint8_t i,j;
    for(i=0;i<n;i++) { c^=(uint32_t)p[i]<<8; for(j=0;j<8;j++) c=(c&0x8000u)?(c<<1)^0x1021u:c<<1; c&=0xFFFF; }
    return (uint16_t)c;
}
void fake_tmp_reset(void) {
    uint8_t i; memset(regs,0,sizeof regs); memset(bad,0,sizeof bad); memset(last,0,sizeof last);
    for(i=0;i<2u*MAX_BANKS;i++) { regs[i][0]=0x0C80; regs[i][2]=1; regs[i][3]=6; regs[i][12]=0x2126; }
}
void fake_tmp_select(uint8_t j) { sensor=j; pos=0; memset(frame,0,sizeof frame); memset(response,0,sizeof response); }
uint8_t fake_tmp_byte(uint8_t byte) {
    uint16_t v,c; uint8_t r;
    if(pos>=6) { ++fake_bus_errors; return 0xFF; }
    frame[pos]=byte;
    if(pos==1) {
        r=frame[1]; if(r>12) { ++fake_bus_errors; return 0xFF; }
        if(tick_ms()-last[sensor]>=250) { regs[sensor][2]|=1; last[sensor]=tick_ms(); }
        v=regs[sensor][r]; response[0]=frame[0]; response[1]=frame[1];
        response[2]=(uint8_t)(v>>8); response[3]=(uint8_t)v; c=crc16(response,4);
        if((frame[0]&1) && bad[sensor]) { --bad[sensor]; c^=1; }
        response[4]=(uint8_t)(c>>8); response[5]=(uint8_t)c;
    }
    return response[pos++];
}
void fake_tmp_end(void) {
    uint8_t r=frame[1]; uint16_t cmd=(uint16_t)(((uint16_t)frame[0]<<8)|r);
    if(r>12 || pos<4) return;
    if(cmd&0x100u) { if(r==0 || r==2) regs[sensor][2]&=0xFFFE; }
    else {
        if((cmd&0x4000u) && (pos!=6 || crc16(frame,4)!=(uint16_t)(((uint16_t)frame[4]<<8)|frame[5]))) {
            regs[sensor][2]|=0x80; return;
        }
        regs[sensor][r]=(uint16_t)(((uint16_t)frame[2]<<8)|frame[3]);
    }
}
void fake_tmp_reg(uint8_t j,uint8_t r,uint16_t v) { regs[j][r]=v; }
void fake_tmp_crc(uint8_t j,uint8_t n) { bad[j]=n; }
