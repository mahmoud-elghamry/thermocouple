#include "app/app_view.h"
#include "app/channel_eval.h"
#include "app/ui.h"
#include "app/ee_owner.h"
#include "services/scan.h"
#include "drivers/relays.h"
#include "mcal/timer.h"
#include "board/board_cfg.h"
#include "app/version.h"
#include <string.h>
#define CAUSES (MAX_CHANNELS+15u+15u*MAX_BANKS)
static temp_dC_t minimum[MAX_CHANNELS],maximum[MAX_CHANNELS];
/* Move-to-front order has no timestamp wrap and includes every G/B instance. */
static uint8_t order[CAUSES],channel_cause[MAX_CHANNELS],trip[(MAX_CHANNELS+7u)/8u];
static uint8_t cursor,count,newest_ch,newest_unit;
static fault_code_t newest;
static uint32_t last_ms,seconds,revision;
static uint16_t fraction;
uint32_t app_uptime_s(void) {
    uint32_t now=tick_ms(),elapsed=now-last_ms;
    last_ms=now;
    if(elapsed<1000u-fraction) fraction=(uint16_t)(fraction+elapsed);
    else { elapsed+=fraction; seconds+=elapsed/1000u; fraction=(uint16_t)(elapsed%1000u); }
    return seconds;
}
const uint8_t *app_trip_bitmap(void) { return trip; }
void app_view_ack(void) {
    uint8_t i;
    memset(trip,0,sizeof trip);
    for(i=0;i<MAX_CHANNELS;i++) minimum[i]=maximum[i]=TEMP_DC_INVALID;
    cursor=0;
}
void app_view_init(void) {
    uint8_t i;
    for(i=0;i<CAUSES;i++) order[i]=i;
    memset(channel_cause,0,sizeof channel_cause);
    last_ms=seconds=0; fraction=0; revision=0; app_view_ack();
}
void app_view_result(uint8_t ch,const result_t *r,act_t action) {
    if(ch>=MAX_CHANNELS) return;
    if(action==ACT_TRIP) trip[ch/8u]|=(uint8_t)(1u<<(ch%8u));
    if(r->flags!=MEAS_VALID || r->temp_dC==TEMP_DC_INVALID) return;
    if(minimum[ch]==TEMP_DC_INVALID || r->temp_dC<minimum[ch]) minimum[ch]=r->temp_dC;
    if(maximum[ch]==TEMP_DC_INVALID || r->temp_dC>maximum[ch]) maximum[ch]=r->temp_dC;
}
void app_view_cause(fault_code_t code,uint8_t channel,uint8_t unit) {
    uint8_t id,i; ch_mode_t mode=CH_MODE_TRIP; act_t action;
    if(channel && channel<=MAX_CHANNELS) {
        id=(uint8_t)(channel-1u); mode=app_settings()->ch[id].mode;
        if(app_settings()->ch[id].type==CH_TYPE_OFF) return;
    } else if(code>=1 && code<=15) id=(uint8_t)(MAX_CHANNELS+code-1u);
    else if(code>=FC_B01_ADC_ID && code<=FC_B15_ADC_RESET && unit<MAX_BANKS)
        id=(uint8_t)(MAX_CHANNELS+15u+(code-FC_B01_ADC_ID)*MAX_BANKS+unit);
    else return;
    /* Temperature causes are evaluated conditions, not registry faults. */
    action=channel && (code==FC_C10_OVER_TRIP || code==FC_C11_OVER_ALARM)?
        chan_action(code==FC_C10_OVER_TRIP?COND_OVER_TRIP:COND_OVER_ALARM,mode):fault_action(code,mode);
    if(action==ACT_NONE) return;
    if(channel) {
        channel_cause[id]=(uint8_t)code;
        if(action==ACT_TRIP) trip[id/8u]|=(uint8_t)(1u<<(id%8u));
    }
    for(i=0;i<CAUSES && order[i]!=id;i++) { }
    if(i<CAUSES) { memmove(order+1,order,i); order[0]=id; }
    cursor=0;
}
static bool present(uint8_t id,fault_code_t *code,uint8_t *ch,uint8_t *unit) {
    const prot_state_t *p=app_protection();
    *ch=*unit=0;
    if(id<MAX_CHANNELS) {
        if(id>=app_settings()->channel_count || app_settings()->ch[id].type==CH_TYPE_OFF || !p->alarm_latch[id]) return false;
        *code=(fault_code_t)channel_cause[id]; *ch=(uint8_t)(id+1u); return *code!=FC_NONE;
    }
    id=(uint8_t)(id-MAX_CHANNELS);
    if(id<15) *code=(fault_code_t)(id+1u);
    else { id=(uint8_t)(id-15u); *code=(fault_code_t)(FC_B01_ADC_ID+id/MAX_BANKS); *unit=(uint8_t)(id%MAX_BANKS); }
    return fault_action(*code,CH_MODE_TRIP)!=ACT_NONE && fault_latched_at(app_faults(),*code,*unit);
}
void app_view_step(void) {
    uint8_t i,ch=ui_channel(),age;
    const scan_out_t *s=scan_last(); const fault_registry_t *f=app_faults();
    (void)app_uptime_s();
    if(revision!=f->active_revision) { cursor=0; revision=f->active_revision; }
    if(!cursor) { count=0; newest=FC_NONE; newest_ch=newest_unit=0; }
    for(i=0;i<8 && cursor<CAUSES;i++,cursor++) {
        fault_code_t code; uint8_t channel,unit;
        if(present(order[cursor],&code,&channel,&unit)) {
            if(!count) { newest=code; newest_ch=channel; newest_unit=unit; }
            ++count;
        }
    }
    if(cursor==CAUSES) { ui_alarm_snapshot(count,newest,newest_ch,newest_unit); cursor=0; }
    if(ch<app_settings()->channel_count) {
        uint8_t b=(uint8_t)(ch/8u); temp_dC_t cj=TEMP_DC_INVALID;
        if(s->scan_no && s->cj_dC[b][0]!=TEMP_DC_INVALID && s->cj_dC[b][1]!=TEMP_DC_INVALID)
            cj=(temp_dC_t)(s->cj_dC[b][0]+(int32_t)(s->cj_dC[b][1]-s->cj_dC[b][0])*board()->channel[ch].cj_weight_q8/256);
        ui_detail_stats(minimum[ch],maximum[ch],cj);
    }
    if(ui_event_request(&age)) {
        event_t event; uint8_t n=0; res_t r=ee_owner_history(age,&n,&event);
        ui_event_result(age,n,r,&event);
    }
}
void mb_io_status(mb_status_t *s) {
    s->now_ms=tick_ms(); s->uptime_s=app_uptime_s(); s->power_cycles=ee_owner_cycles();
    s->version=FW_BUILD_VERSION; s->patch=FW_BUILD_PATCH; s->schema=SETTINGS_SCHEMA_VERSION;
    s->run_driven=relay_run_sense(); s->alarm_driven=relay_alarm_sense();
    memcpy(s->trip_latched,trip,sizeof trip);
}
