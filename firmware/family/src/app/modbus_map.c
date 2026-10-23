#include "app/modbus.h"

static bool fresh(const mb_snapshot_t *s,uint8_t ch) {
    const result_t *r=&s->scan->meas[ch];
    return s->scan->scan_no!=0 && r->scan_no==s->scan->scan_no &&
        s->scan->settings_seq==s->settings->sequence && r->flags==MEAS_VALID &&
        r->temp_dC!=TEMP_DC_INVALID;
}
static bool bit(const uint8_t *p,uint8_t ch) {
    return (p[ch/8u]&(uint8_t)(1u<<(ch%8u)))!=0;
}
static bool channel_fault(const mb_snapshot_t *s,uint8_t ch) {
    uint8_t code;
    for(code=FC_C01_OPEN;code<=FC_C09_RTD;code++)
        if(bit(s->faults->active[code],ch)) return true;
    return false;
}
uint8_t mb_channel_state(const mb_snapshot_t *s,uint8_t ch) {
    const chan_cfg_t *c=&s->settings->ch[ch];
    if(s->cache) return s->cache->state[ch];
    if(c->type==CH_TYPE_OFF) return 0;
    if(!fresh(s,ch) || channel_fault(s,ch) || s->scan->meas[ch].temp_dC>c->probe_limit_dC) return 4;
    if(s->scan->meas[ch].temp_dC>=c->trip_dC) return 3;
    if(s->scan->meas[ch].temp_dC>=c->alarm_dC) return 2;
    return 1;
}
static uint16_t fault_word(const mb_snapshot_t *s,uint8_t word) {
    uint8_t n,j; uint16_t value=0;
    if(s->cache) return s->cache->faults[word];
    for(n=0;n<16;n++) {
        uint8_t code=(uint8_t)(16u*word+n);
        if(code>=FAULT_CODES) break;
        if(code==FC_G04_INTERNAL && s->faults->internal) value|=(uint16_t)(1u<<n);
        for(j=0;j<FAULT_BYTES;j++) if(s->faults->active[code][j]) {
            value|=(uint16_t)(1u<<n); break;
        }
    }
    return value;
}
static uint16_t channel_word(const mb_snapshot_t *s,uint8_t group,uint8_t word) {
    uint8_t n; uint16_t value=0;
    for(n=0;n<16;n++) {
        uint8_t ch=(uint8_t)(16u*word+n); bool set;
        if(ch>=s->settings->channel_count) break;
        if(s->settings->ch[ch].type==CH_TYPE_OFF) continue;
        if(group==0) set=bit(s->status.trip_latched,ch);
        else if(group==1) set=s->protection->alarm_latch[ch]!=0 || mb_channel_state(s,ch)>=2;
        else set=mb_channel_state(s,ch)==4;
        if(set) value|=(uint16_t)(1u<<n);
    }
    return value;
}
static uint16_t alarm_count(const mb_snapshot_t *s) {
    uint8_t code,j,ch; uint16_t count=0;
    if(s->cache) return s->cache->alarms;
    for(ch=0;ch<s->settings->channel_count;ch++) if(mb_channel_state(s,ch)>=2) ++count;
    /* Count active channel alarms once, G/B causes per unit. Informational
     * reset codes are not alarms; a latch without an active cause is not active. */
    for(code=1;code<=FC_B15_ADC_RESET;code++) {
        if(code==FC_G11_RESET_WDT || code==FC_G12_RESET_BOD) continue;
        for(j=0;j<FAULT_BYTES;j++) {
            uint8_t v=s->faults->active[code][j];
            while(v) { ++count; v&=(uint8_t)(v-1u); }
        }
    }
    if(s->faults->internal) {
        bool active=false;
        for(j=0;j<FAULT_BYTES;j++) if(s->faults->active[FC_G04_INTERNAL][j]) active=true;
        if(!active) ++count;
    }
    return count;
}
static uint16_t global(const mb_snapshot_t *s,uint8_t a) {
    const first_out_t *f=&s->protection->first;
    uint32_t age;
    switch(a) {
    case 0: return 1;
    case 1: return s->settings->board_type;
    case 2: return s->settings->channel_count;
    case 3: return s->status.version;
    case 4: return s->status.patch;
    case 5: return s->status.schema;
    case 6: return (uint16_t)s->protection->mode;
    case 7: return s->status.run_driven?1:0;
    case 8: return s->status.alarm_driven?1:0;
    case 9: return alarm_count(s);
    case 10: return f->valid?(uint16_t)f->code:0;
    case 11: return f->valid?f->channel:0;
    case 12: return f->valid?(uint16_t)f->value_dC:0;
    case 13: return f->valid?(uint16_t)f->threshold_dC:0;
    case 14: return (uint16_t)(s->scan->scan_no>>16);
    case 15: return (uint16_t)s->scan->scan_no;
    case 16:
        if(!s->have_validated) return 0x8000;
        age=s->status.now_ms-s->last_validated_ms;
        return age>UINT16_MAX?UINT16_MAX:(uint16_t)age;
    case 17: return (uint16_t)s->status.power_cycles;
    case 18: return (uint16_t)(s->status.uptime_s>>16);
    case 19: return (uint16_t)s->status.uptime_s;
    case 52: return (uint16_t)s->ack_reason;
    default:
        if(a>=20 && a<28) return fault_word(s,(uint8_t)(a-20));
        if(a>=28 && a<52) return channel_word(s,(uint8_t)((a-28)/8),(uint8_t)((a-28)%8));
        return 0;
    }
}
static bool range(const mb_snapshot_t *s,uint16_t start,uint16_t count);
uint16_t mb_register(const mb_snapshot_t *s,uint16_t a) {
    uint8_t ch,offset; const chan_cfg_t *c; const result_t *r;
    if(!s || !s->settings || s->settings->channel_count>MAX_CHANNELS || !range(s,a,1)) return 0;
    if(a<64) return global(s,(uint8_t)a);
    if(a>=600) {
        ch=(uint8_t)((a-600)/3); offset=(uint8_t)(2*((a-600)%3));
        if(ch>=MAX_CHANNELS) return 0;
        return (uint16_t)((uint16_t)(uint8_t)s->settings->ch[ch].name[offset]<<8)|
            (uint8_t)s->settings->ch[ch].name[offset+1];
    }
    ch=(uint8_t)((a-100)/10); offset=(uint8_t)((a-100)%10);
    if(ch>=MAX_CHANNELS) return 0;
    c=&s->settings->ch[ch]; r=&s->scan->meas[ch];
    switch(offset) {
    case 0: return c->type!=CH_TYPE_OFF && fresh(s,ch)?(uint16_t)r->temp_dC:0x8000;
    case 1: return mb_channel_state(s,ch);
    case 2: return c->type==CH_TYPE_OFF?0:(uint16_t)((r->flags&0x0Eu)|
        (fresh(s,ch)?1u:0u)|(bit(s->status.trip_latched,ch)?64u:0u)|
        (s->protection->alarm_latch[ch]?128u:0u));
    case 3: return (uint16_t)c->type;
    case 4: return (uint16_t)c->mode;
    case 5: return (uint16_t)c->alarm_dC;
    case 6: return (uint16_t)c->trip_dC;
    case 7: return c->band_C;
    case 8: return s->age[ch];
    default: return 0;
    }
}
static bool range(const mb_snapshot_t *s,uint16_t start,uint16_t count) {
    uint32_t end=(uint32_t)start+count;
    return (start<64 && end<=64) ||
        (start>=100 && start<100u+10u*MAX_CHANNELS && end<=100u+10u*s->settings->channel_count) ||
        (start>=600 && start<600u+3u*MAX_CHANNELS && end<=600u+3u*s->settings->channel_count);
}
/* Internal core shared with shell, which already checked streaming RX CRC. */
uint16_t mb_prepare(const mb_snapshot_t *s,const uint8_t *r,uint16_t n,uint8_t *out,uint16_t cap,uint16_t *start_out) {
    uint16_t start,count,length; uint8_t address,fn,exception=0;
    if(!s || !s->settings || !s->scan || !s->protection || !s->faults || !s->age ||
       !r || !out || n<4 || n>MB_TX_BYTES || s->settings->channel_count>MAX_CHANNELS ||
       s->settings->address<1 || s->settings->address>247 || r[0]!=s->settings->address || r[0]==0) return 0;
    address=r[0]; fn=r[1];
    if((fn==3 || fn==4 || fn==6) && n!=8) return 0;
    if(fn==16 && (n<9 || n!=(uint16_t)(9u+r[6]))) return 0;
    start=count=0;
    if(fn!=3 && fn!=4) exception=1;
    else {
        start=(uint16_t)((uint16_t)r[2]<<8)|r[3]; count=(uint16_t)((uint16_t)r[4]<<8)|r[5];
        if(count==0 || count>MB_MAX_REGISTERS) exception=3;
        else if(!range(s,start,count)) exception=2;
    }
    length=exception?5:(uint16_t)(5u+2u*count);
    if(cap<length) return 0;
    out[0]=address; out[1]=exception?(uint8_t)(fn|128u):fn;
    out[2]=exception?exception:(uint8_t)(2u*count);
    *start_out=start;
    return length;
}
uint16_t mb_build(const mb_snapshot_t *s,const uint8_t *r,uint16_t n,uint8_t *out,uint16_t cap) {
    uint16_t length,c,start,i;
    if(!r || n<4 || n>MB_TX_BYTES || mb_crc16(r,n)!=0) return 0;
    length=mb_prepare(s,r,n,out,cap,&start);
    if(length) {
        if(!(out[1]&128u)) for(i=0;i<out[2]/2u;i++) {
            uint16_t value=mb_register(s,(uint16_t)(start+i));
            out[3+2*i]=(uint8_t)(value>>8); out[4+2*i]=(uint8_t)value;
        }
        c=mb_crc16(out,(uint16_t)(length-2)); out[length-2]=(uint8_t)c; out[length-1]=(uint8_t)(c>>8);
    }
    return length;
}
