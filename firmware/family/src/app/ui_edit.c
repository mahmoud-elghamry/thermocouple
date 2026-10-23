#include "app/ui.h"
#include <string.h>

void ui_begin(ui_state_t *u,const settings_t *s,bool blank) {
    uint8_t i;
    u->session=true; u->blank=blank; u->base_sequence=s->sequence;
    u->address=blank?1:s->address; u->baud=blank?0:s->baud;
    u->work_pin=blank?0:s->pin_bcd;
    for(i=0;i<UI_CHANNELS;i++) {
        const chan_cfg_t *c=&s->ch[i]; ui_chan_t *w=&u->work[i];
        w->type=blank?0:(uint8_t)c->type; w->mode=blank?0:(uint8_t)c->mode;
        w->alarm=blank?0:c->alarm_dC; w->trip=blank?0:c->trip_dC;
        w->limit=blank?0:c->probe_limit_dC; w->band=blank?2:c->band_C;
        w->epoch=blank?0:c->type_epoch;
        if(blank) memset(w->name,' ',6); else memcpy(w->name,c->name,6);
    }
}
static int16_t field_value(const ui_state_t *u) {
    const ui_chan_t *w=&u->work[u->channel];
    switch(u->field) {
    case UF_TYPE:return w->type&3u; case UF_MODE:return w->mode;
    case UF_ALARM:return ui_whole(w->alarm); case UF_TRIP:return ui_whole(w->trip);
    case UF_BAND:return w->band; case UF_LIMIT:return ui_whole(w->limit);
    case UF_ADDRESS:return u->address; case UF_BAUD:return u->baud;
    default:return 0;
    }
}
void ui_edit_begin(ui_state_t *u) {
    u->edit_value=field_value(u); u->position=0;
    memcpy(u->edit_name,u->work[u->channel].name,6);
    u->screen=UI_EDIT;
}
static void bounds(const ui_state_t *u,int16_t *lo,int16_t *hi,int16_t *step) {
    uint8_t type=u->work[u->channel].type&3u;
    int16_t max=type==CH_TYPE_J?1200:1372;
    *lo=0; *step=1;
    switch(u->field) {
    case UF_TYPE:*hi=2;break; case UF_MODE:case UF_BAUD:*hi=1;break;
    case UF_ADDRESS:*lo=1;*hi=247;break; case UF_BAND:*lo=2;*hi=50;break;
    case UF_LIMIT:*lo=100;*hi=max;*step=10;break;
    default:*hi=max;break;
    }
}
static char next_char(char c,int8_t direction) {
    /* Normative name alphabet, in its displayed order. */
    if(direction>0) {
        if(c>='A' && c<'Z') return (char)(c+1);
        if(c=='Z') return '0';
        if(c>='0' && c<'9') return (char)(c+1);
        if(c=='9') return ' ';
        if(c==' ') return '-';
        if(c=='-') return '/';
        return 'A';
    }
    if(c>'A' && c<='Z') return (char)(c-1);
    if(c=='A') return '/';
    if(c>'0' && c<='9') return (char)(c-1);
    if(c=='0') return 'Z';
    if(c==' ') return '9';
    if(c=='-') return ' ';
    return '-';
}
void ui_edit_key(ui_state_t *u,key_t key) {
    ui_chan_t *w=&u->work[u->channel];
    int16_t lo,hi,step;
    if(key==KEY_ESC) { u->screen=u->field>=UF_ADDRESS?UI_COMMS:UI_FIELDS; return; }
    if(u->field==UF_NAME) {
        if(key==KEY_UP || key==KEY_DOWN) u->edit_name[u->position]=next_char(u->edit_name[u->position],key==KEY_UP?1:-1);
        if(key!=KEY_SET || ++u->position<6) return;
        memcpy(w->name,u->edit_name,6); u->screen=UI_FIELDS; return;
    }
    bounds(u,&lo,&hi,&step);
    if(key==KEY_UP && u->edit_value<hi) {
        u->edit_value=(int16_t)(u->edit_value+step); if(u->edit_value>hi) u->edit_value=hi;
        if(u->edit_value<lo) u->edit_value=lo;
    }
    if(key==KEY_DOWN && u->edit_value>lo) {
        u->edit_value=(int16_t)(u->edit_value-step); if(u->edit_value<lo) u->edit_value=lo;
    }
    if(key!=KEY_SET) return;
    if(u->edit_value<lo || u->edit_value>hi) { u->message=UM_RANGE; return; }
    if(u->field!=UF_TYPE && u->field!=UF_NAME && u->field<UF_ADDRESS && !(w->type&3u)) {
        u->message=UM_OFF; return;
    }
    switch(u->field) {
    case UF_TYPE:
        if((w->type&3u)!=(uint8_t)u->edit_value) {
            w->type=(uint8_t)u->edit_value; /* 05 section 5: epoch belongs to commit. */
            w->alarm=w->trip=w->limit=0;
            if(!w->type) { w->mode=0; w->band=2; }
            else { w->type|=0x70u; if(w->band<2) w->band=2; }
        } break;
    case UF_MODE:w->mode=(uint8_t)u->edit_value;break;
    case UF_ALARM:w->alarm=(int16_t)(u->edit_value*10);w->type&=0xEFu;break;
    case UF_TRIP:w->trip=(int16_t)(u->edit_value*10);w->type&=0xDFu;break;
    case UF_BAND:w->band=(uint8_t)u->edit_value;break;
    case UF_LIMIT:w->limit=(int16_t)(u->edit_value*10);w->type&=0xBFu;break;
    case UF_ADDRESS:u->address=(uint8_t)u->edit_value;break;
    case UF_BAUD:u->baud=(uint8_t)u->edit_value;break;
    default:u->message=UM_INVALID;return;
    }
    u->screen=u->field>=UF_ADDRESS?UI_COMMS:UI_FIELDS;
}
static uint8_t first_bit(uint8_t mask) {
    uint8_t bit=0;
    if(!(mask&15u)) { mask>>=4;bit=4; }
    if(!(mask&3u)) { mask>>=2;bit+=2; }
    return (uint8_t)(bit+((mask&1u)?0:1));
}
static uint8_t last_bit(uint8_t mask) {
    uint8_t bit=0;
    if(mask&0xF0u) { mask>>=4;bit=4; }
    if(mask&12u) { mask>>=2;bit+=2; }
    return (uint8_t)(bit+((mask&2u)?1:0));
}
bool ui_find_diff(ui_state_t *u,const settings_t *s,int8_t direction) {
    uint8_t ch,index=0,first=255,last=255,next=255,last_mask=0,next_mask=0;
    u->protection_change=false;
    for(ch=0;ch<=UI_CHANNELS;ch++) {
        uint8_t mask=0,count=7;
        if(ch==UI_CHANNELS) {
            count=3;
            if(u->address!=s->address) mask|=1;
            if(u->baud!=s->baud) mask|=2;
            if(u->work_pin!=s->pin_bcd) mask|=4;
        } else {
            const ui_chan_t *w=&u->work[ch];const chan_cfg_t *c=&s->ch[ch];
            if((w->type&3u)!=(uint8_t)c->type || w->epoch!=c->type_epoch) mask|=1;
            if(w->mode!=(uint8_t)c->mode) mask|=2;
            if(memcmp(w->name,c->name,6)!=0) mask|=4;
            if(w->alarm!=c->alarm_dC) mask|=8;
            if(w->trip!=c->trip_dC) mask|=16;
            if(w->band!=c->band_C) mask|=32;
            if(w->limit!=c->probe_limit_dC) mask|=64;
            if(mask&0x7Bu) u->protection_change=true;
        }
        if(mask) {
            uint8_t selected=mask;
            if(first==255) first=(uint8_t)(index+first_bit(mask));
            last=index;last_mask=mask;
            if(direction>0 && next==255 && index+count>u->diff) {
                if(index<=u->diff) selected&=(uint8_t)(0xFFu<<(u->diff-index+1u));
                if(selected) next=(uint8_t)(index+first_bit(selected));
            }
            if(direction<0 && index<u->diff) {
                if(u->diff<index+count) selected&=(uint8_t)((1u<<(u->diff-index))-1u);
                if(selected) { next=index;next_mask=selected; }
            }
        }
        index=(uint8_t)(index+count);
    }
    if(first==255) return false;
    u->diff=direction==0?first:direction>0?(next!=255?next:first):
        next!=255?(uint8_t)(next+last_bit(next_mask)):(uint8_t)(last+last_bit(last_mask));
    return true;
}
res_t ui_prepare(ui_state_t *u,const settings_t *s,settings_t *candidate) {
    uint8_t i,first; uint16_t offset,left;
    if(s->sequence!=u->base_sequence) { u->message=UM_STALE;return RES_ERR_RANGE; }
    if(u->blank && u->work_pin==0) { u->message=UM_NEW_PIN;return RES_ERR_RANGE; }
    /* Host and AVR settings_t sizes differ; zero 64 bytes per pass, then
     * expand two compact channels per pass into the existing app mailbox. */
    offset=(uint16_t)(u->entry_mask*64u);
    if(u->position==0 && offset<sizeof *candidate) {
        left=(uint16_t)(sizeof *candidate-offset);if(left>64) left=64;
        memset((uint8_t *)candidate+offset,0,left);u->entry_mask++;
        if((uint16_t)(offset+left)==sizeof *candidate) { u->position=1;u->entry_mask=0; }
        return RES_BUSY;
    }
    if(u->position==1 && u->entry_mask<UI_CHANNELS) {
        candidate->board_type=24;candidate->channel_count=UI_CHANNELS;
        candidate->sequence=s->sequence;candidate->address=u->address;
        candidate->baud=u->baud;candidate->pin_bcd=u->work_pin;
        first=u->entry_mask;
        for(i=first;i<(uint8_t)(first+2);i++) {
            const ui_chan_t *w=&u->work[i]; chan_cfg_t *c=&candidate->ch[i];
            if(w->type&0x70u) { u->message=UM_REENTER;return RES_ERR_RANGE; }
            c->type=(ch_type_t)w->type; c->mode=(ch_mode_t)w->mode; memcpy(c->name,w->name,6);
            c->alarm_dC=w->alarm; c->trip_dC=w->trip; c->probe_limit_dC=w->limit;
            c->band_C=w->band;
            c->type_epoch=u->blank?0:(uint8_t)((s->ch[i].type_epoch+(c->type!=s->ch[i].type?1u:0u))&63u);
            if(c->type!=CH_TYPE_OFF && c->alarm_dC>=c->trip_dC) { u->message=UM_ORDER;return RES_ERR_RANGE; }
            if(c->type!=CH_TYPE_OFF && c->probe_limit_dC<1000) { u->message=UM_RANGE;return RES_ERR_RANGE; }
        }
        u->entry_mask=(uint8_t)(first+2);return RES_BUSY;
    }
    if(set_validate(candidate)!=RES_OK) { u->message=UM_INVALID;return RES_ERR_RANGE; }
    return RES_OK;
}
