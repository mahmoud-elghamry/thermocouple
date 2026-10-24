#include "services/events.h"
#include "settings_bytes.h"
#include <stddef.h>
uint8_t ev_crc8(const uint8_t *p, uint8_t n)
{
    uint8_t crc=0, i, b;
    if(p==NULL) return 0;
    for(i=0;i<n;++i) {
        crc^=p[i];
        for(b=0;b<8;++b) crc=(uint8_t)((crc&0x80u)?((uint8_t)(crc<<1)^0x07u):(uint8_t)(crc<<1));
    }
    return crc;
}
res_t ev_pack(const event_t *e, uint8_t out[16])
{
    if(e==NULL || out==NULL || e->type<EV_POWER_UP || e->type>EV_PIN_RESET ||
       (unsigned)e->code>FC_C11_OVER_ALARM || e->channel>MAX_CHANNELS) return RES_ERR_RANGE;
    put16(out,e->sequence); out[2]=(uint8_t)e->type; out[3]=(uint8_t)e->code; out[4]=e->channel;
    put16(out+5,e->power_cycles); out[7]=(uint8_t)e->uptime_s;
    out[8]=(uint8_t)(e->uptime_s>>8); out[9]=(uint8_t)(e->uptime_s>>16);
    put16(out+10,(uint16_t)e->value_dC); put16(out+12,(uint16_t)e->threshold_dC);
    out[14]=e->unit; out[15]=ev_crc8(out,15); return RES_OK;
}
res_t ev_unpack(const uint8_t in[16], event_t *e)
{
    if(in==NULL || e==NULL) return RES_ERR_RANGE;
    if(ev_crc8(in,15)!=in[15]) return RES_ERR_CRC;
    if(in[2]<1 || in[2]>10 || in[3]>51 || in[4]>MAX_CHANNELS) return RES_ERR_RANGE;
    e->sequence=get16(in); e->type=(event_type_t)in[2]; e->code=(fault_code_t)in[3];
    e->channel=in[4]; e->power_cycles=get16(in+5);
    e->uptime_s=(uint32_t)in[7]|((uint32_t)in[8]<<8)|((uint32_t)in[9]<<16);
    e->value_dC=geti16(in+10); e->threshold_dC=geti16(in+12); e->unit=in[14]; return RES_OK;
}
int ev_newest(const events_t *r)
{
    int newest=-1; uint16_t seq=0; uint8_t i; event_t e;
    if(r==NULL) return -1;
    for(i=0;i<EVENT_SLOTS;++i) if(ev_unpack(r->slot[i],&e)==RES_OK) {
        uint16_t delta=(uint16_t)(e.sequence-seq);
        if(newest<0 || (delta!=0 && delta<0x8000u)) { newest=i; seq=e.sequence; }
    }
    return newest;
}
int ev_log(events_t *r, const event_t *e)
{
    int newest; event_t next, prev; uint8_t slot;
    if(r==NULL || e==NULL) return -1;
    newest=ev_newest(r); next=*e;
    if(newest>=0) { (void)ev_unpack(r->slot[newest],&prev); next.sequence=(uint16_t)(prev.sequence+1u); }
    else next.sequence=0;
    slot=(uint8_t)((newest+1)%EVENT_SLOTS);
    return ev_pack(&next,r->slot[slot])==RES_OK?(int)slot:-1;
}
res_t ev_get(const events_t *r, uint8_t age, event_t *e)
{
    int newest;
    if(r==NULL || age>=EVENT_SLOTS || e==NULL) return RES_ERR_RANGE;
    newest=ev_newest(r); if(newest<0) return RES_ERR_RANGE;
    return ev_unpack(r->slot[((unsigned)newest+EVENT_SLOTS-age)%EVENT_SLOTS],e);
}
