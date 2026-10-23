#include "app/protection.h"
#include "services/events.h"
#include <string.h>
#include "app/timing.h"
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
    memset(s->fitted,0xFF,sizeof(s->fitted));
}
static void remember_channels(prot_state_t *s, const settings_t *cfg)
{
    uint8_t ch;
    memset(s->fitted,0,sizeof(s->fitted));
    for(ch=0;ch<cfg->channel_count;++ch) if(cfg->ch[ch].type!=CH_TYPE_OFF)
        s->fitted[ch/8u]|=(uint8_t)(1u<<(ch%8u));
}
bool prot_begin_pass(prot_state_t *s,const settings_t *cfg)
{
    s->pass_cfg=cfg; s->pass_prepared=true; s->pass_valid=set_validate(cfg)==RES_OK;
    if(s->pass_valid) remember_channels(s,cfg);
    return s->pass_valid;
}
static bool newer_result(const prot_state_t *s,uint8_t ch,const scan_out_t *scan)
{
    return (s->latest_seen[ch/8u]&(1u<<(ch%8u))) &&
        (scan==NULL || (int32_t)(s->latest_scan[ch]-scan->scan_no)>0);
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
/* cfg was validated at the pass boundary: both thresholds and the largest
 * 500 dC reset band fit int16_t, including a negative reset threshold. */
static bool reset_clear(const result_t *r,const chan_cfg_t *c,cond_t cond,bool trip_limit)
{
    if(c->type==CH_TYPE_OFF || (trip_limit && c->mode==CH_MODE_ALARM_ONLY)) return true;
    if(cond!=COND_NORMAL && !(trip_limit && cond==COND_OVER_ALARM)) return false;
    return c->band_C>=2 && c->band_C<=50 && r->temp_dC<=(int16_t)(
        (trip_limit?c->trip_dC:c->alarm_dC)-(int16_t)c->band_C*10);
}
bool prot_on_result(prot_state_t *s, uint8_t ch, const result_t *r, const settings_t *cfg,
                    uint32_t scan_no, uint32_t uptime_s)
{
    cond_t cond; act_t act; fault_code_t cause; bool fresh;
    if(s==NULL) return false;
    bool prepared=s->pass_prepared && s->pass_cfg==cfg;
    if(!prot_integrity(s) || cfg==NULL || (prepared?!s->pass_valid:set_validate(cfg)!=RES_OK) || ch>=cfg->channel_count || ch>=MAX_CHANNELS) {
        mode_set(s,TRIPPED); first(s,FC_G04_INTERNAL,0,0,0,0,uptime_s); s->ack_released=false; return true;
    }
    if(!prepared) remember_channels(s,cfg);
    if((s->latest_seen[ch/8u]&(1u<<(ch%8u))) && (int32_t)(scan_no-s->latest_scan[ch])<0) return false;
    cond=chan_cond(r,&cfg->ch[ch],scan_no); act=chan_action(cond,cfg->ch[ch].mode);
    s->latest_scan[ch]=scan_no; s->latest_seen[ch/8u]|=(uint8_t)(1u<<(ch%8u));
    { uint8_t bit=(uint8_t)(1u<<(ch%8u)),byte=(uint8_t)(ch/8u);
      s->alarm_clear[byte]&=(uint8_t)~bit;
      if(reset_clear(r,&cfg->ch[ch],cond,false)) s->alarm_clear[byte]|=bit;
      s->trip_clear[byte]&=(uint8_t)~bit;
      if(reset_clear(r,&cfg->ch[ch],cond,true)) s->trip_clear[byte]|=bit;
    }
    cause=chan_cause(r,cond); fresh=act==ACT_TRIP && s->trip_seen[ch]!=(uint8_t)cause;
    if(act!=ACT_NONE) s->alarm_latch[ch]=1;
    if(act==ACT_TRIP) {
        if(fresh || s->mode==RUN) trip(s,cause,(uint8_t)(ch+1u),0,r?r->temp_dC:TEMP_DC_INVALID,cfg->ch[ch].trip_dC,uptime_s);
        s->trip_seen[ch]=(uint8_t)cause;
    } else s->trip_seen[ch]=0;
    return fresh;
}
static act_t notify_fault(prot_state_t *s,fault_code_t code,uint8_t unit,ch_mode_t mode,
                          uint8_t channel,uint32_t uptime_s,bool fresh)
{
    act_t action=fault_action(code,mode);
    if(s==NULL) return action;
    if(!prot_integrity(s) || unit>=FAULT_UNITS || code<1 || code>=FAULT_CODES) {
        mode_set(s,TRIPPED); first(s,FC_G04_INTERNAL,0,0,0,0,uptime_s); s->ack_released=false; return ACT_TRIP;
    }
    if(code>=FC_C01_OPEN && code<=FC_C09_RTD && unit<MAX_CHANNELS &&
       !(s->fitted[unit/8u]&(1u<<(unit%8u)))) action=ACT_NONE;
    if((code==FC_G01_SETTINGS_INVALID || code==FC_G10_CALIBRATION) && s->mode!=SERVICE) {
        mode_set(s,CONFIG_LOCK); s->ack_released=false;
    } else if(action==ACT_TRIP && (fresh || s->mode==RUN)) trip(s,code,channel,unit,0,0,uptime_s);
    return action;
}
bool prot_on_fault(prot_state_t *s,fault_registry_t *reg,fault_code_t code,
                   uint8_t unit,ch_mode_t mode,uint8_t channel,uint32_t uptime_s)
{
    bool fresh=fault_raise(reg,code,unit);
    (void)notify_fault(s,code,unit,mode,channel,uptime_s,fresh); return fresh;
}
act_t prot_observe_fault(prot_state_t *s,fault_registry_t *reg,fault_code_t code,
                        uint8_t unit,ch_mode_t mode,uint8_t channel,uint32_t uptime_s)
{
    if((code>FC_G15_FUSES && code<FC_B01_ADC_ID) || (code>FC_B15_ADC_RESET && code<FC_C01_OPEN) ||
       code<1 || code>=FAULT_CODES || unit>=FAULT_UNITS) (void)fault_raise(reg,code,unit);
    return notify_fault(s,code,unit,mode,channel,uptime_s,true);
}
static fault_code_t first_fault(const fault_registry_t *reg, uint8_t *unit)
{
    return fault_first_trip(reg,unit);
}
static bool fresh_scan(const prot_in_t *in, bool current_settings)
{
    uint8_t i, banks;
    if(in->scan==NULL || in->settings==NULL || !in->scan->scan_validated ||
       (current_settings && in->scan->settings_seq!=in->settings->sequence) ||
       (uint32_t)(in->now_ms-in->scan->completed_ms)>=APP_SCAN_DEADLINE_MS) return false;
    banks=in->settings->board_type==40?6u:(uint8_t)(in->settings->channel_count/8u);
    for(i=0;i<banks;++i) if(in->scan->bank[i]!=BANK_VALIDATED) return false;
    return true;
}
static void clear_alarms(const prot_in_t *in, prot_state_t *s)
{
    uint8_t ch;
    if(in->scan!=NULL && in->settings!=NULL && in->settings->channel_count<=MAX_CHANNELS)
        for(ch=0;ch<in->settings->channel_count;++ch)
            if(((in->scan_unchanged && (s->latest_seen[ch/8u]&(1u<<(ch%8u)))) ||
                newer_result(s,ch,in->scan))?(s->alarm_clear[ch/8u]&(1u<<(ch%8u)))!=0:
               chan_alarm_clear(&in->scan->meas[ch],&in->settings->ch[ch],in->scan->scan_no)) s->alarm_latch[ch]=0;
    fault_ack(in->faults);
}
/* C registry units at this boundary are normalized zero-based channels.
 * Acquisition maps a raw CM pin to its channel before publication; the raw pin
 * identity belongs in the event value field. */
static fault_code_t channel_fault(const fault_registry_t *reg, uint8_t ch, bool latched)
{
    uint8_t code,bit=(uint8_t)(1u<<(ch%8u)),byte=(uint8_t)(ch/8u);
    const uint8_t (*map)[FAULT_BYTES];
    if(reg==NULL || ch>=MAX_CHANNELS) return FC_C01_OPEN;
    map=latched?reg->latch:reg->active;
    for(code=FC_C01_OPEN;code<=FC_C09_RTD;++code) {
        if(code==FC_C04_RATE_RESERVED || code==FC_C05_STUCK_RESERVED) continue;
        if(map[code][byte]&bit) return (fault_code_t)code;
    }
    return FC_NONE;
}
static void channel_masks(const fault_registry_t *reg,uint8_t *active,uint8_t *latched)
{
    uint8_t b,c;
    for(b=0;b<(MAX_CHANNELS+7u)/8u;b++) {
        uint8_t a=0,l=0;
        for(c=FC_C01_OPEN;c<=FC_C09_RTD;c++) {
            if(c==FC_C04_RATE_RESERVED || c==FC_C05_STUCK_RESERVED) continue;
            a|=reg->active[c][b]; l|=reg->latch[c][b];
        }
        active[b]=a; latched[b]=l;
    }
}
static void ack(const prot_in_t *in,prot_state_t *s,prot_out_t *out,bool cfg_ok,
                fault_code_t cause,uint8_t unit,const uint8_t *active_channels)
{
    uint8_t ch; bool cached;
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
    if(cause!=FC_NONE) {
        out->ack_reason=ACK_R3_FAULT; first(s,cause,0,unit,0,0,in->uptime_s); return;
    }
    cached=in->scan_unchanged && s->clear_valid && s->clear_scan==in->scan->scan_no &&
        s->clear_settings==in->settings->sequence;
    for(ch=0;ch<in->settings->channel_count;++ch)
        if(!(cached?
             (s->completed_clear[ch/8u]&(1u<<(ch%8u)))!=0:
             chan_trip_clear(&in->scan->meas[ch],&in->settings->ch[ch],in->scan->scan_no)) ||
           (in->settings->ch[ch].type!=CH_TYPE_OFF && in->settings->ch[ch].mode==CH_MODE_TRIP && (active_channels[ch/8u]&(1u<<(ch%8u))))) {
            out->ack_reason=ACK_R4_CHANNEL; out->refusal_channel=(uint8_t)(ch+1u);
            cond_t cond=chan_cond(&in->scan->meas[ch],&in->settings->ch[ch],in->scan->scan_no);
            fault_code_t code=channel_fault(in->faults,ch,false);
            if(code!=FC_NONE || chan_action(cond,in->settings->ch[ch].mode)==ACT_TRIP)
                first(s,code!=FC_NONE?code:chan_cause(&in->scan->meas[ch],cond),
                      (uint8_t)(ch+1u),0,in->scan->meas[ch].temp_dC,in->settings->ch[ch].trip_dC,in->uptime_s);
            return;
        }
    if(!cfg_ok || in->writing) { out->ack_reason=ACK_R5_SETTINGS; return; }
    if(!in->readback_off_ok) { out->ack_reason=ACK_R6_RELAY; return; }
    mode_set(s,RUN); memset(&s->first,0,sizeof(s->first));
    s->accepted_settings_seq=in->settings->sequence; s->replaced_sequence_valid=false;
    memset(s->trip_seen,0,sizeof(s->trip_seen));
    /* clear_alarms already ran above; intervening checks cannot change any
     * result or registry latch. A second whole-registry ACK is redundant. */
    /* Await a new validated scan before starting the pump; expiry still trips. */
    s->window_started_ms=in->now_ms; s->window_valid=false; out->event_mask|=EVENT_BIT(EV_ACK);
}
void prot_step(const prot_in_t *in, prot_state_t *s, prot_out_t *out)
{
    bool cfg_ok, cal_ok, was_running; uint8_t ch, unit=0; fault_code_t cause; prot_mode_t before;
    uint8_t active_channels[(MAX_CHANNELS+7u)/8u],latched_channels[(MAX_CHANNELS+7u)/8u];
    if(out==NULL) return;
    memset(out,0,sizeof(*out)); out->alarm_active=true;
    if(in==NULL || s==NULL) return;
    before=s->mode;
    if(!prot_integrity(s)) {
        (void)fault_raise(in->faults,FC_G04_INTERNAL,0);
        mode_set(s,TRIPPED); first(s,FC_G04_INTERNAL,0,0,0,0,in->uptime_s); s->ack_released=false;
    }
    if(!s->pass_prepared || s->pass_cfg!=in->settings) (void)prot_begin_pass(s,in->settings);
    cfg_ok=in->settings_valid && s->pass_valid;
    cal_ok=in->calibration_valid;
    if(s->mode!=SERVICE && (!cfg_ok || !cal_ok)) {
        (void)fault_raise(in->faults,cfg_ok?FC_G10_CALIBRATION:FC_G01_SETTINGS_INVALID,0);
        mode_set(s,CONFIG_LOCK); s->ack_released=false;
    }
    if(in->commit_begin && in->protection_change && s->mode!=SERVICE && s->mode!=CONFIG_LOCK) {
        mode_set(s,START_LATCHED); s->ack_released=false;
    }
    if(in->protection_change && (in->commit_begin || in->commit_done)) memset(s->latest_seen,0,sizeof s->latest_seen);
    if(in->commit_done && cfg_ok && cal_ok) {
        fault_clear(in->faults,FC_G01_SETTINGS_INVALID,0); fault_clear(in->faults,FC_G10_CALIBRATION,0);
        if(s->mode==CONFIG_LOCK || (in->protection_change && s->mode!=SERVICE)) mode_set(s,START_LATCHED);
        if(s->mode==RUN && in->settings->sequence!=s->accepted_settings_seq) {
            s->replaced_settings_seq=s->accepted_settings_seq;
            /* Each save increments by one (05 §5). A gap means an unseen save;
             * the last accepted generation is no longer the one just replaced. */
            s->replaced_sequence_valid=(uint32_t)(in->settings->sequence-s->accepted_settings_seq)==1u;
            s->accepted_settings_seq=in->settings->sequence;
        }
        s->ack_released=false;
        out->event_mask|=EVENT_BIT(in->protection_change?EV_SETTINGS_CHANGED:EV_NAME_CHANGED);
    }
    /* Expiry is handled BEFORE accepting a late scan. */
    if(s->mode==RUN && (uint32_t)(in->now_ms-s->window_started_ms)>=APP_RUN_WINDOW_MS) {
        (void)prot_on_fault(s,in->faults,FC_G05_SCAN_DEADLINE,0,CH_MODE_TRIP,0,in->uptime_s);
    }
    cause=first_fault(in->faults,&unit);
    if(cause!=FC_NONE && s->mode==RUN) trip(s,cause,0,unit,0,0,in->uptime_s);
    if(in->scan_complete && !in->results_evaluated && cfg_ok && in->scan!=NULL) {
        for(ch=0;ch<in->settings->channel_count;++ch) {
            bool had=s->alarm_latch[ch]!=0;
            if(prot_on_result(s,ch,&in->scan->meas[ch],in->settings,in->scan->scan_no,in->uptime_s))
                out->event_mask|=EVENT_BIT(EV_TRIP);
            if(!had && s->alarm_latch[ch]) out->event_mask|=EVENT_BIT(EV_ALARM);
        }
    }
    if(in->scan_complete && cfg_ok && in->scan!=NULL) {
        s->clear_valid=true; s->clear_scan=in->scan->scan_no; s->clear_settings=in->settings->sequence;
        memcpy(s->completed_clear,s->trip_clear,sizeof s->completed_clear);
        for(ch=0;ch<in->settings->channel_count;ch++)
            if(!(s->latest_seen[ch/8u]&(1u<<(ch%8u))) || s->latest_scan[ch]!=in->scan->scan_no) s->clear_valid=false;
    }
    if(cfg_ok && in->faults!=NULL) channel_masks(in->faults,active_channels,latched_channels);
    else { memset(active_channels,0xFF,sizeof active_channels); memset(latched_channels,0xFF,sizeof latched_channels); }
    if(cfg_ok && in->settings!=NULL) for(ch=0;ch<in->settings->channel_count;++ch) {
        const chan_cfg_t *c=&in->settings->ch[ch];
        if(c->type==CH_TYPE_OFF) continue;
        if(active_channels[ch/8u]&(1u<<(ch%8u))) {
            fault_code_t code=channel_fault(in->faults,ch,false);
            s->alarm_latch[ch]=1;
            if(c->mode==CH_MODE_TRIP && s->mode==RUN) trip(s,code,(uint8_t)(ch+1u),0,0,0,in->uptime_s);
        }
        if(in->scan!=NULL && !in->scan_complete && !in->scan_unchanged && !newer_result(s,ch,in->scan) && chan_action(chan_cond(&in->scan->meas[ch],c,in->scan->scan_no),c->mode)!=ACT_NONE)
            s->alarm_latch[ch]=1;
    }
    if(in->ack_key_released && !in->ack) s->ack_released=true;
    was_running=s->mode==RUN;
    ack(in,s,out,cfg_ok && cal_ok,cause,unit,active_channels);
    if(in->ack && in->faults!=NULL) channel_masks(in->faults,active_channels,latched_channels);
    /* Only an observed names-only commit permits one replaced scan generation.
     * ACK's completion belongs to the preceding state, never to its new window. */
    if(was_running && s->mode==RUN && in->scan_complete && fresh_scan(in,false) &&
       in->settings->sequence==s->accepted_settings_seq &&
       (in->scan->settings_seq==s->accepted_settings_seq ||
        (s->replaced_sequence_valid && in->scan->settings_seq==s->replaced_settings_seq)) &&
       cause==FC_NONE && in->flow_ok) {
        s->window_valid=true; s->window_started_ms=in->now_ms; out->window_refresh=true;
        if(in->scan->settings_seq==s->accepted_settings_seq) s->replaced_sequence_valid=false;
    }
    out->run_permission=prot_integrity(s) && s->mode==RUN && cfg_ok && cal_ok &&
        cause==FC_NONE && in->flow_ok;
    if(out->run_permission && s->window_valid && (uint32_t)(in->now_ms-s->window_started_ms)<APP_RUN_WINDOW_MS)
        out->window_remaining_ms=(uint16_t)(APP_RUN_WINDOW_MS-(uint32_t)(in->now_ms-s->window_started_ms));
    out->alarm_active=s->mode!=RUN || !cfg_ok || !cal_ok || !in->flow_ok || fault_global_alarm_latched(in->faults);
    if(cfg_ok) for(ch=0;ch<in->settings->channel_count;++ch)
        if(in->settings->ch[ch].type!=CH_TYPE_OFF &&
           (s->alarm_latch[ch] || (latched_channels[ch/8u]&(1u<<(ch%8u))))) out->alarm_active=true;
    if(before!=TRIPPED && s->mode==TRIPPED) out->event_mask|=EVENT_BIT(EV_TRIP);
    s->pass_prepared=false;
}
