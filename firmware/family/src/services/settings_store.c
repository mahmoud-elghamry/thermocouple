#include "services/settings.h"
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
            if(candidate->ch[i].type_epoch!=expected) return RES_ERR_RANGE;
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
            if(active->ch[i].type_epoch==63 && candidate->ch[i].type_epoch==0) {
                next_cal.baseline_nV[i]=CAL_MISSING; next_cal.tag[i]=0;
            }
        if(cal_pack(&next_cal,st->wrap_cal_image)!=RES_OK) return RES_ERR_RANGE;
    }
    next=*candidate; next.sequence=active?active->sequence+1u:0;
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
