#include "services/settings.h"
#include "settings_bytes.h"
#include <string.h>
res_t cal_validate(const calibration_t *c)
{
    uint8_t i;
    if(c==NULL || c->bank_count<1 || c->bank_count>MAX_BANKS) return RES_ERR_RANGE;
    for(i=0;i<MAX_BANKS;++i) {
        if(i>=c->bank_count) { if(c->ref_ppm[i]!=0) return RES_ERR_RANGE; }
        else if(c->ref_ppm[i]!=CAL_MISSING && (c->ref_ppm[i]<-10000 || c->ref_ppm[i]>10000)) return RES_ERR_RANGE;
    }
    for(i=0;i<MAX_CHANNELS;++i) {
        if(c->baseline_nV[i]==CAL_MISSING) { if(c->tag[i]!=0) return RES_ERR_RANGE; }
        else if(c->baseline_nV[i]<1500000 || c->baseline_nV[i]>10000000 ||
                ((c->tag[i]&3u)!=1u && (c->tag[i]&3u)!=2u)) return RES_ERR_RANGE;
    }
    return RES_OK;
}
res_t cal_pack(const calibration_t *c, uint8_t out[CAL_SLOT_SIZE])
{
    uint8_t i;
    if(out==NULL || cal_validate(c)!=RES_OK) return RES_ERR_RANGE;
    memset(out,0,CAL_SLOT_SIZE); put16(out,0x434C); out[2]=1; out[3]=c->bank_count;
    put32(out+4,c->sequence);
    for(i=0;i<MAX_BANKS;++i) put32(out+8u+4u*i,(uint32_t)c->ref_ppm[i]);
    for(i=0;i<MAX_CHANNELS;++i) {
        put32(out+32u+4u*i,(uint32_t)c->baseline_nV[i]); out[204u+i]=c->tag[i];
    }
    put16(out+247,set_crc16(out,247)); return RES_OK;
}
res_t cal_pack_part(const calibration_t *c,uint8_t *out,uint8_t first,uint8_t count)
{
    uint8_t i;
    if(c==NULL || out==NULL || first>MAX_BANKS+MAX_CHANNELS || count>MAX_BANKS+MAX_CHANNELS-first) return RES_ERR_RANGE;
    if(first==0) { put16(out,0x434C); out[2]=1; out[3]=c->bank_count; put32(out+4,c->sequence); }
    for(i=first;i<(uint8_t)(first+count);i++) {
        if(i<MAX_BANKS) put32(out+8u+4u*i,(uint32_t)c->ref_ppm[i]);
        else { uint8_t ch=(uint8_t)(i-MAX_BANKS);
            put32(out+32u+4u*ch,(uint32_t)c->baseline_nV[ch]); out[204u+ch]=c->tag[ch]; }
    }
    return RES_OK;
}
res_t cal_unpack(const uint8_t in[CAL_SLOT_SIZE], uint8_t banks, calibration_t *c)
{
    uint8_t i;
    if(in==NULL || c==NULL) return RES_ERR_RANGE;
    memset(c,0,sizeof(*c));
    if(get16(in)!=0x434C || in[2]!=1 || in[3]!=banks) return RES_ERR_RANGE;
    if(get16(in+247)!=set_crc16(in,247)) return RES_ERR_CRC;
    c->bank_count=banks; c->sequence=get32(in+4);
    for(i=0;i<MAX_BANKS;++i) c->ref_ppm[i]=geti32(in+8u+4u*i);
    for(i=0;i<MAX_CHANNELS;++i) { c->baseline_nV[i]=geti32(in+32u+4u*i); c->tag[i]=in[204u+i]; }
    return cal_validate(c);
}
bool cal_complete(const calibration_t *c, const settings_t *s)
{
    if(cal_validate(c)!=RES_OK || set_validate(s)!=RES_OK) return false;
    return cal_bindings_complete(c,s);
}
bool cal_bindings_complete(const calibration_t *c,const settings_t *s)
{
    uint8_t i,banks;
    if(!c || !s || s->channel_count>MAX_CHANNELS) return false;
    banks=(uint8_t)(s->channel_count/8u);
    if(c->bank_count!=banks) return false;
    for(i=0;i<banks;++i) if(c->ref_ppm[i]==CAL_MISSING) return false;
    for(i=0;i<s->channel_count;++i) if(s->ch[i].type!=CH_TYPE_OFF) {
        if(c->baseline_nV[i]==CAL_MISSING ||
           c->tag[i]!=(uint8_t)((s->ch[i].type_epoch<<2)|(uint8_t)s->ch[i].type)) return false;
    }
    return true;
}
res_t cal_learn(calibration_t *c, const settings_t *s, const int32_t baseline_nV[MAX_CHANNELS])
{
    uint8_t i;
    if(cal_validate(c)!=RES_OK || set_validate(s)!=RES_OK || baseline_nV==NULL) return RES_ERR_RANGE;
    for(i=0;i<s->channel_count;++i) if(s->ch[i].type!=CH_TYPE_OFF &&
        (baseline_nV[i]<1500000 || baseline_nV[i]>10000000)) return RES_ERR_RANGE;
    for(i=0;i<s->channel_count;++i) if(s->ch[i].type!=CH_TYPE_OFF) {
        c->baseline_nV[i]=baseline_nV[i];
        c->tag[i]=(uint8_t)((s->ch[i].type_epoch<<2)|(uint8_t)s->ch[i].type);
    }
    return RES_OK;
}
