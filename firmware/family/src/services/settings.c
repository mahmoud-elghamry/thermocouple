#include "services/settings.h"
#include "settings_bytes.h"
#include <string.h>

uint16_t set_crc16(const uint8_t *p, size_t n)
{
    uint16_t crc=0xFFFF;
    size_t i; uint8_t bit;
    if(p==NULL || n>SETTINGS_SLOT_SIZE) return 0;
    for(i=0;i<n;++i) {
        crc^=(uint16_t)((uint16_t)p[i]<<8);
        for(bit=0;bit<8;++bit)
            crc=(uint16_t)((crc&0x8000u)?((uint16_t)(crc<<1)^0x1021u):(uint16_t)(crc<<1));
    }
    return crc;
}
res_t set_validate(const settings_t *s)
{
    uint8_t i, j, fitted=0;
    if(s==NULL) return RES_ERR_RANGE;
    if(!((s->board_type==8 && s->channel_count==8) ||
         (s->board_type==24 && s->channel_count==24) ||
         (s->board_type==40 && s->channel_count==43))) return RES_ERR_RANGE;
    if(s->address<1 || s->address>247 || s->baud>1) return RES_ERR_RANGE;
    for(i=0;i<4;++i) if(((s->pin_bcd>>(4u*i))&15u)>9u) return RES_ERR_RANGE;
    for(i=0;i<s->channel_count;++i) {
        const chan_cfg_t *c=&s->ch[i]; int16_t max;
        for(j=0;j<6;++j) if((uint8_t)c->name[j]<0x20 || (uint8_t)c->name[j]>0x7E) return RES_ERR_RANGE;
        if(c->type_epoch>63 || (c->mode!=CH_MODE_TRIP && c->mode!=CH_MODE_ALARM_ONLY)) return RES_ERR_RANGE;
        switch(c->type) {
        case CH_TYPE_OFF:
            if(c->mode!=CH_MODE_TRIP || c->alarm_dC!=0 || c->trip_dC!=0 ||
               c->band_C!=2 || c->probe_limit_dC!=0) return RES_ERR_RANGE;
            continue;
        case CH_TYPE_K: max=13720; break;
        case CH_TYPE_J: max=12000; break;
        case CH_TYPE_PT100: max=4000; break;
        default: return RES_ERR_RANGE;
        }
        if((i>=40)!=(c->type==CH_TYPE_PT100)) return RES_ERR_RANGE;
        if(c->band_C<2 || c->band_C>50 || c->alarm_dC<0 || c->alarm_dC>=c->trip_dC ||
           c->trip_dC>c->probe_limit_dC || c->probe_limit_dC>max) return RES_ERR_RANGE;
        ++fitted;
    }
    return fitted?RES_OK:RES_ERR_RANGE;
}
res_t set_pack(const settings_t *s, uint8_t out[SETTINGS_SLOT_SIZE])
{
    uint8_t i; uint16_t end;
    if(out==NULL || set_validate(s)!=RES_OK) return RES_ERR_RANGE;
    memset(out,0,SETTINGS_SLOT_SIZE);
    put16(out,0x5354); out[2]=1; out[3]=s->board_type; out[4]=s->channel_count;
    put32(out+6,s->sequence); out[10]=s->address; out[11]=s->baud; put16(out+12,s->pin_bcd);
    for(i=0;i<s->channel_count;++i) {
        const chan_cfg_t *c=&s->ch[i]; uint8_t *p=out+16u+16u*i;
        p[0]=(uint8_t)c->type; p[1]=(uint8_t)c->mode; memcpy(p+2,c->name,6);
        put16(p+8,(uint16_t)c->alarm_dC); put16(p+10,(uint16_t)c->trip_dC);
        p[12]=c->band_C; p[13]=c->type_epoch; put16(p+14,(uint16_t)c->probe_limit_dC);
    }
    end=(uint16_t)(16u+16u*s->channel_count); put16(out+end,set_crc16(out,end));
    return RES_OK;
}
res_t set_unpack(const uint8_t in[SETTINGS_SLOT_SIZE], uint8_t board_type,
                 uint8_t channel_count, settings_t *s)
{
    uint8_t i; uint16_t end;
    if(in==NULL || s==NULL || channel_count>MAX_CHANNELS) return RES_ERR_RANGE;
    memset(s,0,sizeof(*s));
    if(get16(in)!=0x5354 || in[2]!=1 || in[3]!=board_type || in[4]!=channel_count ||
       in[5]!=0 || in[14]!=0 || in[15]!=0) return RES_ERR_RANGE;
    end=(uint16_t)(16u+16u*channel_count);
    if(get16(in+end)!=set_crc16(in,end)) return RES_ERR_CRC;
    s->board_type=in[3]; s->channel_count=in[4]; s->sequence=get32(in+6);
    s->address=in[10]; s->baud=in[11]; s->pin_bcd=get16(in+12);
    for(i=0;i<channel_count;++i) {
        chan_cfg_t *c=&s->ch[i]; const uint8_t *p=in+16u+16u*i;
        c->type=(ch_type_t)p[0]; c->mode=(ch_mode_t)p[1]; memcpy(c->name,p+2,6);
        c->alarm_dC=geti16(p+8); c->trip_dC=geti16(p+10); c->band_C=p[12];
        c->type_epoch=p[13]; c->probe_limit_dC=geti16(p+14);
    }
    return set_validate(s);
}
int set_select(bool av, uint32_t a, bool bv, uint32_t b)
{
    uint32_t d=b-a;
    if(!av) return bv?1:-1;
    if(!bv) return 0;
    return (d!=0 && d<UINT32_C(0x80000000))?1:0;
}
bool set_protection_changed(const settings_t *a, const settings_t *b)
{
    uint8_t i;
    if(a==NULL || b==NULL || a->board_type!=b->board_type || a->channel_count!=b->channel_count ||
       a->channel_count>MAX_CHANNELS) return true;
    for(i=0;i<a->channel_count;++i) {
        const chan_cfg_t *x=&a->ch[i], *y=&b->ch[i];
        if(x->type!=y->type || x->mode!=y->mode || x->alarm_dC!=y->alarm_dC ||
           x->trip_dC!=y->trip_dC || x->band_C!=y->band_C ||
           x->probe_limit_dC!=y->probe_limit_dC || x->type_epoch!=y->type_epoch) return true;
    }
    return false;
}
res_t set_change_type(chan_cfg_t *c, ch_type_t type)
{
    if(c==NULL || (unsigned)type>CH_TYPE_PT100 || c->type_epoch>63) return RES_ERR_RANGE;
    if(type==c->type) return RES_OK;
    c->type=type; c->type_epoch=(uint8_t)((c->type_epoch+1u)&63u);
    c->alarm_dC=0; c->trip_dC=0; c->probe_limit_dC=0;
    if(type==CH_TYPE_OFF) { c->mode=CH_MODE_TRIP; c->band_C=2; }
    return RES_OK;
}
