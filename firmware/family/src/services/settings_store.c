#include "services/settings.h"
#include "settings_bytes.h"
#include <string.h>
void set_store_init(set_store_t *st)
{
    if(st!=NULL) { memset(st,0,sizeof(*st)); st->active_slot=2; st->calibration_active_slot=2; }
}
static bool available(const set_store_t *st)
{ return st->phase==STORE_IDLE || st->phase==STORE_DONE || st->phase==STORE_FAILED; }
static void begin(set_store_t *s, uint8_t active, uint16_t size, bool cal, bool prot)
{
    s->phase=STORE_INVALIDATE; s->active_slot=active;
    s->target_slot=active==0?1:0;
    s->base=(uint16_t)(cal?(0x640u+256u*s->target_slot):(0x40u+768u*s->target_slot));
    s->length=size; s->index=2; s->pending=false; s->retries=0;
    s->calibration=cal; s->protection_change=prot;
    s->settings_after_cal=false;
    if(cal) { s->calibration_active_slot=active; s->calibration_slot_known=true; }
}
static res_t settings_commit(set_store_t *st, const settings_t *candidate,
                             const settings_t *active, uint8_t active_slot,
                             const calibration_t *cal, uint8_t cal_slot)
{
    settings_t next; calibration_t next_cal; uint8_t i; bool wraps=false;
    if(st==NULL || active_slot>2 || set_validate(candidate)!=RES_OK) return RES_ERR_RANGE;
    if(!available(st)) return RES_BUSY;
    if(active!=NULL) {
        if(active_slot>1 || set_validate(active)!=RES_OK || candidate->board_type!=active->board_type ||
           candidate->channel_count!=active->channel_count) return RES_ERR_RANGE;
        /* Epoch changes are enforced at the commit boundary, not trusted to UI. */
        for(i=0;i<active->channel_count;++i) {
            uint8_t expected=active->ch[i].type_epoch;
            if(active->ch[i].type!=candidate->ch[i].type) expected=(uint8_t)((expected+1u)&63u);
            if(active->ch[i].type_epoch==63 && expected==0) wraps=true;
        }
    } else if(active_slot!=2) return RES_ERR_RANGE;
    if(wraps) {
        uint8_t banks=candidate->board_type==40?6u:(uint8_t)(candidate->channel_count/8u);
        if(cal_slot>1 || cal_validate(cal)!=RES_OK || cal->bank_count!=banks) return RES_ERR_RANGE;
        /* A settings verification failure may leave its copy boot-selectable.
         * Never overwrite the verified cleared calibration using a stale slot
         * on retry: that would briefly expose the ancient baseline again. */
        if(st->calibration_slot_known && cal_slot!=st->calibration_active_slot) return RES_ERR_RANGE;
        next_cal=*cal; next_cal.sequence=cal->sequence+1u;
        for(i=0;i<active->channel_count;++i)
            if(active->ch[i].type_epoch==63 && active->ch[i].type!=candidate->ch[i].type) {
                next_cal.baseline_nV[i]=CAL_MISSING; next_cal.tag[i]=0;
            }
        if(cal_pack(&next_cal,st->wrap_cal_image)!=RES_OK) return RES_ERR_RANGE;
    }
    next=*candidate; next.sequence=active?active->sequence+1u:0;
    if(active) for(i=0;i<active->channel_count;i++)
        next.ch[i].type_epoch=(uint8_t)((active->ch[i].type_epoch+(next.ch[i].type!=active->ch[i].type?1u:0u))&63u);
    if(set_pack(&next,st->image)!=RES_OK) return RES_ERR_RANGE;
    begin(st,active_slot,(uint16_t)(18u+16u*next.channel_count),false,set_protection_changed(active,&next));
    if(wraps) {
        begin(st,cal_slot,249,true,true);
        st->active_slot=active_slot; st->settings_after_cal=true;
    }
    return RES_OK;
}
res_t set_commit(set_store_t *st, const settings_t *candidate, const settings_t *active, uint8_t active_slot)
{
    return settings_commit(st,candidate,active,active_slot,NULL,2);
}
res_t set_commit_with_cal(set_store_t *st, const settings_t *candidate,
                          const settings_t *active, uint8_t active_slot,
                          const calibration_t *active_cal, uint8_t cal_slot)
{
    return settings_commit(st,candidate,active,active_slot,active_cal,cal_slot);
}
res_t cal_commit(set_store_t *st, const calibration_t *candidate, uint32_t active_sequence, uint8_t active_slot)
{
    calibration_t next;
    if(st==NULL || active_slot>2 || cal_validate(candidate)!=RES_OK) return RES_ERR_RANGE;
    if(!available(st)) return RES_BUSY;
    if(st->calibration_slot_known && active_slot!=st->calibration_active_slot) return RES_ERR_RANGE;
    next=*candidate; next.sequence=active_slot==2?0:active_sequence+1u;
    if(cal_pack(&next,st->image)!=RES_OK) return RES_ERR_RANGE;
    begin(st,active_slot,249,true,true); return RES_OK;
}
enum { PREP_NEW,PREP_OLD,PREP_EPOCH,PREP_CAL_CHECK,PREP_ZERO,PREP_SETTINGS,
       PREP_CAL,PREP_SETTINGS_CRC,PREP_CAL_CRC,PREP_FINISH };
res_t set_prepare_with_cal(set_store_t *s,const settings_t *candidate,const settings_t *active,
                          uint8_t slot,const calibration_t *cal,uint8_t cal_slot)
{
    if(!s || !candidate || slot>2 || candidate->channel_count>MAX_CHANNELS) return RES_ERR_RANGE;
    if(!available(s)) return RES_BUSY;
    if(active?(slot>1 || active->channel_count!=candidate->channel_count || active->board_type!=candidate->board_type):slot!=2)
        return RES_ERR_RANGE;
    s->protection_change=set_protection_changed(active,candidate);
    s->prep_candidate=candidate; s->prep_active=active; s->prep_cal=cal;
    s->prep_sequence=active?active->sequence+1u:0; s->prep_cal_slot=cal_slot;
    s->active_slot=slot; s->phase=STORE_PREPARE; s->prep_stage=PREP_NEW;
    s->prep_cursor=0; s->prep_position=0; s->prep_fitted=s->prep_wrap=s->prep_cal_only=false;
    s->pending=false; s->calibration=false;
    memset(s->prep_wrap_mask,0,sizeof s->prep_wrap_mask); return RES_OK;
}
res_t cal_prepare(set_store_t *s,const calibration_t *candidate,uint32_t sequence,uint8_t slot)
{
    if(!s || !candidate || slot>2) return RES_ERR_RANGE;
    if(!available(s)) return RES_BUSY;
    if(s->calibration_slot_known && slot!=s->calibration_active_slot) return RES_ERR_RANGE;
    s->prep_cal=candidate; s->prep_candidate=s->prep_active=NULL;
    s->prep_sequence=slot==2?0:sequence+1u; s->active_slot=slot;
    s->protection_change=s->calibration=s->prep_cal_only=true;
    s->pending=s->prep_wrap=false; s->prep_position=0; s->prep_cursor=0;
    s->phase=STORE_PREPARE; s->prep_stage=PREP_CAL_CHECK; return RES_OK;
}
static void prepare_fail(set_store_t *s)
{
    s->phase=STORE_FAILED;
    if(s->fault!=FC_G02_SAVE_FAIL_PROT) s->fault=s->protection_change?FC_G02_SAVE_FAIL_PROT:FC_G13_SAVE_FAIL_INFO;
}
static void prepare_step(set_store_t *s)
{
    uint8_t n,i; uint16_t end; uint8_t *out;
    const settings_t *cfg=s->prep_candidate,*old=s->prep_active;
    const calibration_t *cal=s->prep_cal;
    switch(s->prep_stage) {
    case PREP_NEW: case PREP_OLD: {
        const settings_t *p=s->prep_stage==PREP_NEW?cfg:old;
        n=(uint8_t)(p->channel_count-s->prep_cursor); if(n>4) n=4;
        if(set_validate_part(p,s->prep_cursor,n,&s->prep_fitted)!=RES_OK) { prepare_fail(s); return; }
        s->prep_cursor=(uint8_t)(s->prep_cursor+n);
        if(s->prep_cursor<p->channel_count) return;
        if(!s->prep_fitted) { prepare_fail(s); return; }
        s->prep_stage=(uint8_t)(s->prep_stage==PREP_NEW && old?PREP_OLD:PREP_EPOCH);
        s->prep_cursor=0; s->prep_fitted=false; return;
    }
    case PREP_EPOCH:
        if(old) {
            end=(uint16_t)(s->prep_cursor+4u); if(end>cfg->channel_count) end=cfg->channel_count;
            for(i=s->prep_cursor;i<end;i++) {
                uint8_t expected=old->ch[i].type_epoch;
                if(old->ch[i].type!=cfg->ch[i].type) expected=(uint8_t)((expected+1u)&63u);
                if(old->ch[i].type_epoch==63 && expected==0) {
                    s->prep_wrap=true; s->prep_wrap_mask[i/8u]|=(uint8_t)(1u<<(i%8u));
                }
            }
            s->prep_cursor=(uint8_t)end; if(end<cfg->channel_count) return;
        }
        s->prep_stage=PREP_CAL_CHECK; return;
    case PREP_CAL_CHECK:
        if(s->prep_wrap || s->prep_cal_only) {
            if(cal_validate(cal)!=RES_OK || (s->prep_wrap &&
               (s->prep_cal_slot>1 || cal->bank_count!=(cfg->board_type==40?6u:cfg->channel_count/8u) ||
                (s->calibration_slot_known && s->prep_cal_slot!=s->calibration_active_slot)))) {
                prepare_fail(s); return;
            }
        }
        s->prep_stage=PREP_ZERO; s->prep_position=0; return;
    case PREP_ZERO:
        out=s->prep_position<SETTINGS_SLOT_SIZE?s->image+s->prep_position:s->wrap_cal_image+s->prep_position-SETTINGS_SLOT_SIZE;
        memset(out,0,64); s->prep_position+=64;
        if(s->prep_position<(s->prep_wrap?SETTINGS_SLOT_SIZE+CAL_SLOT_SIZE:SETTINGS_SLOT_SIZE)) return;
        s->prep_cursor=0; s->prep_stage=s->prep_cal_only?PREP_CAL:PREP_SETTINGS; return;
    case PREP_SETTINGS:
        n=(uint8_t)(cfg->channel_count-s->prep_cursor); if(n>4) n=4;
        if(set_pack_part(cfg,s->image,s->prep_cursor,n)!=RES_OK) { prepare_fail(s); return; }
        if(old) for(i=s->prep_cursor;i<(uint8_t)(s->prep_cursor+n);i++)
            s->image[16u+16u*i+13u]=(uint8_t)((old->ch[i].type_epoch+(cfg->ch[i].type!=old->ch[i].type?1u:0u))&63u);
        if(s->prep_cursor==0) put32(s->image+6,s->prep_sequence);
        s->prep_cursor=(uint8_t)(s->prep_cursor+n);
        if(s->prep_cursor<cfg->channel_count) return;
        s->prep_cursor=0; s->prep_position=0; s->prep_crc=0xFFFF;
        s->prep_stage=s->prep_wrap?PREP_CAL:PREP_SETTINGS_CRC; return;
    case PREP_CAL:
        out=s->prep_cal_only?s->image:s->wrap_cal_image;
        n=(uint8_t)(MAX_BANKS+MAX_CHANNELS-s->prep_cursor); if(n>8) n=8;
        if(cal_pack_part(cal,out,s->prep_cursor,n)!=RES_OK) { prepare_fail(s); return; }
        if(s->prep_cursor==0) put32(out+4,s->prep_cal_only?s->prep_sequence:cal->sequence+1u);
        for(i=s->prep_cursor;i<(uint8_t)(s->prep_cursor+n);i++) if(i>=MAX_BANKS && s->prep_wrap) {
            uint8_t ch=(uint8_t)(i-MAX_BANKS);
            if(s->prep_wrap_mask[ch/8u]&(1u<<(ch%8u))) { put32(out+32u+4u*ch,(uint32_t)CAL_MISSING); out[204u+ch]=0; }
        }
        s->prep_cursor=(uint8_t)(s->prep_cursor+n);
        if(s->prep_cursor<MAX_BANKS+MAX_CHANNELS) return;
        s->prep_position=0; s->prep_crc=0xFFFF;
        s->prep_stage=s->prep_cal_only?PREP_CAL_CRC:PREP_SETTINGS_CRC; return;
    case PREP_SETTINGS_CRC: case PREP_CAL_CRC:
        out=s->prep_stage==PREP_SETTINGS_CRC || s->prep_cal_only?s->image:s->wrap_cal_image;
        end=s->prep_stage==PREP_SETTINGS_CRC?(uint16_t)(16u+16u*cfg->channel_count):247;
        n=(uint8_t)(end-s->prep_position>16?16:end-s->prep_position);
        s->prep_crc=set_crc16_continue(s->prep_crc,out+s->prep_position,n); s->prep_position+=n;
        if(s->prep_position<end) return;
        put16(out+end,s->prep_crc); s->prep_position=0; s->prep_crc=0xFFFF;
        s->prep_stage=s->prep_stage==PREP_SETTINGS_CRC && s->prep_wrap?PREP_CAL_CRC:PREP_FINISH; return;
    case PREP_FINISH: {
        uint8_t slot=s->active_slot; bool prot=s->protection_change;
        if(s->prep_cal_only) begin(s,slot,249,true,true);
        else {
            begin(s,slot,(uint16_t)(18u+16u*cfg->channel_count),false,prot);
            if(s->prep_wrap) { begin(s,s->prep_cal_slot,249,true,true); s->active_slot=slot; s->settings_after_cal=true; }
        }
        return;
    }
    default: prepare_fail(s); return;
    }
}
static void retry_or_fail(set_store_t *s)
{
    s->pending=false;
    if(s->fault!=FC_G02_SAVE_FAIL_PROT) s->fault=s->protection_change?FC_G02_SAVE_FAIL_PROT:FC_G13_SAVE_FAIL_INFO;
    if(s->retries==0) { s->retries=1; s->phase=STORE_INVALIDATE; s->index=2; }
    else s->phase=STORE_FAILED;
}
static const uint8_t *store_image(const set_store_t *s)
{ return s->settings_after_cal?s->wrap_cal_image:s->image; }
void set_store_step(set_store_t *s, bool ready, bool success, uint8_t value, ee_op_t *op)
{
    if(op==NULL) return;
    memset(op,0,sizeof(*op));
    if(s==NULL || !ready) return;
    if(s->phase==STORE_PREPARE) { prepare_step(s); return; }
    if(s->phase==STORE_IDLE || s->phase==STORE_DONE || s->phase==STORE_FAILED) return;
    if(s->pending) {
        s->pending=false;
        if(!success || (s->phase==STORE_VERIFY && value!=store_image(s)[s->index])) retry_or_fail(s);
        else switch(s->phase) {
        case STORE_INVALIDATE: s->phase=STORE_BODY; s->index=2; break;
        case STORE_BODY:
            ++s->index;
            if(s->index==s->length) { s->phase=STORE_MAGIC; s->index=1; }
            break;
        case STORE_MAGIC:
            if(s->index==1) s->index=0;
            else { s->phase=STORE_VERIFY; s->index=0; }
            break;
        case STORE_VERIFY:
            ++s->index;
            if(s->index==s->length) {
                if(s->settings_after_cal) {
                    uint8_t settings_slot=s->active_slot, cal_slot=s->target_slot;
                    begin(s,settings_slot,(uint16_t)(18u+16u*s->image[4]),false,true);
                    s->calibration_active_slot=cal_slot;
                } else {
                    s->phase=STORE_DONE; s->active_slot=s->target_slot;
                    if(s->calibration) s->calibration_active_slot=s->target_slot;
                    if(s->fault!=FC_G02_SAVE_FAIL_PROT || s->protection_change) s->fault=FC_NONE;
                }
            }
            break;
        default: retry_or_fail(s); break;
        }
    }
    switch(s->phase) {
    case STORE_INVALIDATE: op->kind=EE_WRITE; op->address=s->base; op->value=0; break;
    case STORE_BODY: case STORE_MAGIC:
        op->kind=EE_WRITE; op->address=(uint16_t)(s->base+s->index); op->value=store_image(s)[s->index]; break;
    case STORE_VERIFY: op->kind=EE_READ; op->address=(uint16_t)(s->base+s->index); break;
    case STORE_DONE: case STORE_FAILED: case STORE_IDLE: return;
    default: s->phase=STORE_FAILED; s->fault=FC_G02_SAVE_FAIL_PROT; return;
    }
    s->pending=true;
}
