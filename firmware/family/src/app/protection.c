#include "app/protection.h"
#include "services/events.h"
#include <string.h>
#define WINDOW_MS 900u
#define EVENT_BIT(e) ((uint16_t)(1u<<((e)-1u)))
static void mode_set(prot_state_t *s, prot_mode_t mode)
{
    s->mode=mode; s->mode_inv=(uint8_t)~(uint8_t)mode;
    s->permit=(mode==RUN)?1:0; s->permit_inv=(uint8_t)~s->permit;
    if(mode!=RUN) s->window_valid=false;
}
bool prot_integrity(const prot_state_t *s)
{
    return s!=NULL && (unsigned)s->mode<=SERVICE &&
        (uint8_t)(s->mode_inv^(uint8_t)s->mode)==UINT8_MAX &&
        (uint8_t)(s->permit_inv^s->permit)==UINT8_MAX &&
        s->permit==((s->mode==RUN)?1u:0u);
}
void prot_init(prot_state_t *s, bool settings_ok, bool cal_ok, bool service)
{
    if(s==NULL) return;
    memset(s,0,sizeof(*s)); mode_set(s,service?SERVICE:((settings_ok&&cal_ok)?START_LATCHED:CONFIG_LOCK));
}
static void first(prot_state_t *s, fault_code_t code, uint8_t channel, uint8_t unit,
                   temp_dC_t value, temp_dC_t threshold, uint32_t uptime)
{
    if(s->first.valid) return;
    s->first.valid=true; s->first.code=code; s->first.channel=channel; s->first.unit=unit;
    s->first.value_dC=value; s->first.threshold_dC=threshold; s->first.uptime_s=uptime;
}
static void trip(prot_state_t *s, fault_code_t code, uint8_t channel, uint8_t unit,
                  temp_dC_t value, temp_dC_t threshold, uint32_t uptime)
{
    s->ack_released=false;
    if(s->mode==RUN || s->mode==TRIPPED) {
        first(s,code,channel,unit,value,threshold,uptime); mode_set(s,TRIPPED);
    }
}
bool prot_on_result(prot_state_t *s, uint8_t ch, const result_t *r, const settings_t *cfg,
                    uint32_t scan_no, uint32_t uptime_s)
{
    cond_t cond; act_t act; fault_code_t cause; bool fresh;
    if(s==NULL) return false;
    if(!prot_integrity(s) || cfg==NULL || set_validate(cfg)!=RES_OK || ch>=cfg->channel_count || ch>=MAX_CHANNELS) {
        mode_set(s,TRIPPED); first(s,FC_G04_INTERNAL,0,0,0,0,uptime_s); s->ack_released=false; return true;
    }
    cond=chan_cond(r,&cfg->ch[ch],scan_no); act=chan_action(cond,cfg->ch[ch].mode);
    cause=chan_cause(r,cond); fresh=act==ACT_TRIP && s->trip_seen[ch]!=(uint8_t)cause;
    if(act!=ACT_NONE) s->alarm_latch[ch]=1;
    if(act==ACT_TRIP) {
        if(fresh || s->mode==RUN) trip(s,cause,(uint8_t)(ch+1u),0,r?r->temp_dC:TEMP_DC_INVALID,cfg->ch[ch].trip_dC,uptime_s);
        s->trip_seen[ch]=(uint8_t)cause;
    } else s->trip_seen[ch]=0;
    return fresh;
}
bool prot_on_fault(prot_state_t *s, fault_registry_t *reg, fault_code_t code,
                   uint8_t unit, ch_mode_t mode, uint8_t channel, uint32_t uptime_s)
{
    bool fresh=fault_raise(reg,code,unit); act_t action=fault_action(code,mode);
    if(s==NULL) return fresh;
    if(!prot_integrity(s) || unit>=FAULT_UNITS || code<1 || code>=FAULT_CODES) {
        mode_set(s,TRIPPED); first(s,FC_G04_INTERNAL,0,0,0,0,uptime_s); s->ack_released=false; return true;
    }
    if((code==FC_G01_SETTINGS_INVALID || code==FC_G10_CALIBRATION) && s->mode!=SERVICE) {
        mode_set(s,CONFIG_LOCK); s->ack_released=false;
    } else if(action==ACT_TRIP && (fresh || s->mode==RUN)) trip(s,code,channel,unit,0,0,uptime_s);
    return fresh;
}
static fault_code_t first_fault(const fault_registry_t *reg, uint8_t *unit)
{
    uint8_t c, u;
    if(reg==NULL || reg->internal) { *unit=0; return FC_G04_INTERNAL; }
    for(c=1;c<=35;++c) {
        if(c>=16 && c<=20) continue;
        if(fault_action((fault_code_t)c,CH_MODE_TRIP)!=ACT_TRIP) continue;
        for(u=0;u<FAULT_UNITS;++u) if(fault_at(reg,(fault_code_t)c,u)) {
            *unit=u; return (fault_code_t)c;
        }
    }
    *unit=0; return FC_NONE;
}
static bool fresh_scan(const prot_in_t *in, bool current_settings)
{
    uint8_t i, banks;
    if(in->scan==NULL || in->settings==NULL || !in->scan->scan_validated ||
       (current_settings && in->scan->settings_seq!=in->settings->sequence) ||
       (uint32_t)(in->now_ms-in->scan->completed_ms)>=1000u) return false;
    banks=in->settings->board_type==40?6u:(uint8_t)(in->settings->channel_count/8u);
    for(i=0;i<banks;++i) if(in->scan->bank[i]!=BANK_VALIDATED) return false;
    return true;
}
static void clear_alarms(const prot_in_t *in, prot_state_t *s)
{
    uint8_t ch;
    if(in->scan!=NULL && in->settings!=NULL && in->settings->channel_count<=MAX_CHANNELS)
        for(ch=0;ch<in->settings->channel_count;++ch)
            if(chan_alarm_clear(&in->scan->meas[ch],&in->settings->ch[ch],in->scan->scan_no)) s->alarm_latch[ch]=0;
    fault_ack(in->faults);
}
/* C registry units at this boundary are normalized zero-based channels.
 * A raw CM pin must be mapped by acquisition before publication (shared header
 * currently allows both encodings; raw pin identity belongs in the event). */
static fault_code_t channel_fault(const fault_registry_t *reg, uint8_t ch)
{
    uint8_t code;
    for(code=FC_C01_OPEN;code<=FC_C09_RTD;++code) {
        if(code==FC_C04_RATE_RESERVED || code==FC_C05_STUCK_RESERVED) continue;
        if(fault_at(reg,(fault_code_t)code,ch)) return (fault_code_t)code;
    }
    return FC_NONE;
}
static void ack(const prot_in_t *in, prot_state_t *s, prot_out_t *out, bool cfg_ok)
{
    uint8_t ch, unit=0; fault_code_t cause;
    if(!in->ack) return;
    if(!s->ack_released || in->ack_held_ms<50 || in->ack_age_ms>500) {
        out->ack_reason=ACK_R1_RELEASE; return;
    }
    /* Consume this command: a held key cannot be replayed through this API. */
    s->ack_released=false;
    clear_alarms(in,s);
    if(s->mode==RUN) { out->event_mask|=EVENT_BIT(EV_ACK); return; }
    if(s->mode!=START_LATCHED && s->mode!=TRIPPED) { out->ack_reason=ACK_R5_SETTINGS; return; }
    if(!fresh_scan(in,true)) { out->ack_reason=ACK_R2_SCAN; return; }
    cause=first_fault(in->faults,&unit);
    if(cause!=FC_NONE) {
        out->ack_reason=ACK_R3_FAULT; first(s,cause,0,unit,0,0,in->uptime_s); return;
    }
    for(ch=0;ch<in->settings->channel_count;++ch)
        if(!chan_trip_clear(&in->scan->meas[ch],&in->settings->ch[ch],in->scan->scan_no) ||
           (in->settings->ch[ch].type!=CH_TYPE_OFF && in->settings->ch[ch].mode==CH_MODE_TRIP && channel_fault(in->faults,ch)!=FC_NONE)) {
            out->ack_reason=ACK_R4_CHANNEL; out->refusal_channel=(uint8_t)(ch+1u);
            cond_t cond=chan_cond(&in->scan->meas[ch],&in->settings->ch[ch],in->scan->scan_no);
            fault_code_t code=channel_fault(in->faults,ch);
            if(code!=FC_NONE || chan_action(cond,in->settings->ch[ch].mode)==ACT_TRIP)
                first(s,code!=FC_NONE?code:chan_cause(&in->scan->meas[ch],cond),
                      (uint8_t)(ch+1u),0,in->scan->meas[ch].temp_dC,in->settings->ch[ch].trip_dC,in->uptime_s);
            return;
        }
    if(!cfg_ok || in->writing) { out->ack_reason=ACK_R5_SETTINGS; return; }
    if(!in->readback_off_ok) { out->ack_reason=ACK_R6_RELAY; return; }
    mode_set(s,RUN); memset(&s->first,0,sizeof(s->first));
    memset(s->trip_seen,0,sizeof(s->trip_seen)); clear_alarms(in,s);
    /* Await a new validated scan before starting the pump; expiry still trips. */
    s->window_started_ms=in->now_ms; s->window_valid=false; out->event_mask|=EVENT_BIT(EV_ACK);
}
void prot_step(const prot_in_t *in, prot_state_t *s, prot_out_t *out)
{
    bool cfg_ok, cal_ok; uint8_t ch, unit=0; fault_code_t cause; prot_mode_t before;
    if(out==NULL) return;
    memset(out,0,sizeof(*out)); out->alarm_active=true;
    if(in==NULL || s==NULL) return;
    before=s->mode;
    if(!prot_integrity(s)) {
        (void)fault_raise(in->faults,FC_G04_INTERNAL,0);
        mode_set(s,TRIPPED); first(s,FC_G04_INTERNAL,0,0,0,0,in->uptime_s); s->ack_released=false;
    }
    cfg_ok=in->settings_valid && set_validate(in->settings)==RES_OK;
    cal_ok=in->calibration_valid;
    if(s->mode!=SERVICE && (!cfg_ok || !cal_ok)) {
        (void)fault_raise(in->faults,cfg_ok?FC_G10_CALIBRATION:FC_G01_SETTINGS_INVALID,0);
        mode_set(s,CONFIG_LOCK); s->ack_released=false;
    }
    if(in->commit_begin && in->protection_change && s->mode!=SERVICE && s->mode!=CONFIG_LOCK) {
        mode_set(s,START_LATCHED); s->ack_released=false;
    }
    if(in->commit_done && cfg_ok && cal_ok) {
        fault_clear(in->faults,FC_G01_SETTINGS_INVALID,0); fault_clear(in->faults,FC_G10_CALIBRATION,0);
        if(s->mode==CONFIG_LOCK || (in->protection_change && s->mode!=SERVICE)) mode_set(s,START_LATCHED);
        s->ack_released=false;
        out->event_mask|=EVENT_BIT(in->protection_change?EV_SETTINGS_CHANGED:EV_NAME_CHANGED);
    }
    /* Expiry is handled BEFORE accepting a late scan. */
    if(s->mode==RUN && (uint32_t)(in->now_ms-s->window_started_ms)>=WINDOW_MS) {
        (void)prot_on_fault(s,in->faults,FC_G05_SCAN_DEADLINE,0,CH_MODE_TRIP,0,in->uptime_s);
    }
    cause=first_fault(in->faults,&unit);
    if(cause!=FC_NONE && s->mode==RUN) trip(s,cause,0,unit,0,0,in->uptime_s);
    if(in->scan_complete && cfg_ok && in->scan!=NULL) {
        for(ch=0;ch<in->settings->channel_count;++ch) {
            bool had=s->alarm_latch[ch]!=0;
            if(prot_on_result(s,ch,&in->scan->meas[ch],in->settings,in->scan->scan_no,in->uptime_s))
                out->event_mask|=EVENT_BIT(EV_TRIP);
            if(!had && s->alarm_latch[ch]) out->event_mask|=EVENT_BIT(EV_ALARM);
        }
    }
    if(cfg_ok && in->settings!=NULL) for(ch=0;ch<in->settings->channel_count;++ch) {
        const chan_cfg_t *c=&in->settings->ch[ch];
        fault_code_t code=channel_fault(in->faults,ch);
        if(c->type==CH_TYPE_OFF) continue;
        if(code!=FC_NONE) {
            s->alarm_latch[ch]=1;
            if(c->mode==CH_MODE_TRIP && s->mode==RUN) trip(s,code,(uint8_t)(ch+1u),0,0,0,in->uptime_s);
        }
        if(in->scan!=NULL && chan_action(chan_cond(&in->scan->meas[ch],c,in->scan->scan_no),c->mode)!=ACT_NONE)
            s->alarm_latch[ch]=1;
    }
    if(in->ack_key_released && !in->ack) s->ack_released=true;
    ack(in,s,out,cfg_ok && cal_ok);
    /* RUN survived a settings sequence change only if protection fields did not
     * change. A names-only save therefore need not discard a straddling scan. */
    if(s->mode==RUN && in->scan_complete && fresh_scan(in,false) &&
       !fault_trip_active(in->faults) && in->flow_ok) {
        s->window_valid=true; s->window_started_ms=in->now_ms; out->window_refresh=true;
    }
    out->run_permission=prot_integrity(s) && s->mode==RUN && cfg_ok && cal_ok &&
        !fault_trip_active(in->faults) && in->flow_ok;
    if(out->run_permission && s->window_valid && (uint32_t)(in->now_ms-s->window_started_ms)<WINDOW_MS)
        out->window_remaining_ms=(uint16_t)(WINDOW_MS-(uint32_t)(in->now_ms-s->window_started_ms));
    out->alarm_active=s->mode!=RUN || !cfg_ok || !cal_ok || !in->flow_ok || fault_alarm_latched(in->faults);
    for(ch=0;ch<MAX_CHANNELS;++ch) if(s->alarm_latch[ch]) out->alarm_active=true;
    if(before!=TRIPPED && s->mode==TRIPPED) out->event_mask|=EVENT_BIT(EV_TRIP);
}
