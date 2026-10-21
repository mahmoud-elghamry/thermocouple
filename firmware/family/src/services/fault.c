#include "services/fault.h"
#include <string.h>
static bool known(fault_code_t c)
{
    return (c>=1 && c<=15) || (c>=21 && c<=35) || (c>=41 && c<=51);
}
act_t fault_action(fault_code_t code, ch_mode_t mode)
{
    if(code==FC_NONE || code==FC_G11_RESET_WDT || code==FC_G12_RESET_BOD ||
       code==FC_C04_RATE_RESERVED || code==FC_C05_STUCK_RESERVED ||
       code==FC_C10_OVER_TRIP || code==FC_C11_OVER_ALARM) return ACT_NONE;
    if(!known(code)) return ACT_TRIP;
    if(code==FC_G13_SAVE_FAIL_INFO) return ACT_ALARM;
    if(code>=FC_C01_OPEN && code<=FC_C09_RTD) {
        if(mode==CH_MODE_ALARM_ONLY) return ACT_ALARM;
        return ACT_TRIP;
    }
    return ACT_TRIP;
}
void fault_init(fault_registry_t *r) { if(r!=NULL) memset(r,0,sizeof(*r)); }
bool fault_at(const fault_registry_t *r, fault_code_t c, uint8_t u)
{
    if(c==FC_NONE) return false;
    if(r==NULL || !known(c) || u>=FAULT_UNITS) return true;
    if(c==FC_G04_INTERNAL && r->internal) return true;
    return (r->active[c][u/8u]&(1u<<(u%8u)))!=0;
}
bool fault_raise(fault_registry_t *r, fault_code_t c, uint8_t u)
{
    bool fresh;
    if(r==NULL) return true;
    if(c==FC_NONE) return false;
    if(!known(c) || u>=FAULT_UNITS) { fresh=!r->internal; r->internal=true; return fresh; }
    fresh=!fault_at(r,c,u); r->active[c][u/8u]|=(uint8_t)(1u<<(u%8u));
    if(fault_action(c,CH_MODE_TRIP)!=ACT_NONE) r->latch[c][u/8u]|=(uint8_t)(1u<<(u%8u));
    return fresh;
}
void fault_clear(fault_registry_t *r, fault_code_t c, uint8_t u)
{
    if(r==NULL) return;
    if(c==FC_NONE) return;
    if(!known(c) || u>=FAULT_UNITS) { r->internal=true; return; }
    if(c==FC_G15_FUSES || c==FC_G03_FLASH_CRC) return;
    r->active[c][u/8u]&=(uint8_t)~(1u<<(u%8u));
}
bool fault_active(const fault_registry_t *r, fault_code_t c)
{
    uint8_t i;
    if(c==FC_NONE) return false;
    if(r==NULL || !known(c)) return true;
    if(c==FC_G04_INTERNAL && r->internal) return true;
    for(i=0;i<FAULT_BYTES;++i) if(r->active[c][i]) return true;
    return false;
}
bool fault_trip_active(const fault_registry_t *r)
{
    uint8_t unit; return fault_first_trip(r,&unit)!=FC_NONE;
}
fault_code_t fault_first_trip(const fault_registry_t *r,uint8_t *unit)
{
    uint8_t c,b,bit;
    *unit=0;
    if(r==NULL || r->internal) return FC_G04_INTERNAL;
    for(c=1;c<=FC_B15_ADC_RESET;++c) {
        if((c>=16 && c<=20) || c==11 || c==12 || c==13) continue;
        for(b=0;b<FAULT_BYTES;++b) {
            uint8_t bits=r->active[c][b];
            if(!bits) continue;
            for(bit=0;bit<8;++bit) if(bits&(1u<<bit)) {
                *unit=(uint8_t)(8*b+bit); return (fault_code_t)c;
            }
        }
    }
    return FC_NONE;
}
bool fault_alarm_latched(const fault_registry_t *r)
{
    uint16_t n; const uint8_t *p;
    if(r==NULL || r->internal) return true;
    p=&r->latch[1][0];
    for(n=FAULT_BYTES;n<FAULT_CODES*FAULT_BYTES;++n) if(*p++) return true;
    return false;
}
bool fault_global_alarm_latched(const fault_registry_t *r)
{
    uint16_t n; const uint8_t *p;
    if(r==NULL || r->internal) return true;
    p=&r->latch[1][0];
    for(n=FAULT_BYTES;n<FC_C01_OPEN*FAULT_BYTES;++n) if(*p++) return true;
    return false;
}
bool fault_latched_at(const fault_registry_t *r, fault_code_t c, uint8_t u)
{
    if(c==FC_NONE) return false;
    if(r==NULL || !known(c) || u>=FAULT_UNITS) return true;
    if(c==FC_G04_INTERNAL && r->internal) return true;
    return (r->latch[c][u/8u]&(1u<<(u%8u)))!=0;
}
void fault_ack(fault_registry_t *r)
{
    uint16_t n; uint8_t *l; const uint8_t *a;
    if(r==NULL) return;
    l=&r->latch[1][0]; a=&r->active[1][0];
    for(n=FAULT_BYTES;n<FAULT_CODES*FAULT_BYTES;++n) { *l++&=*a++; }
}
