#include "app/channel_eval.h"
#include <stddef.h>
cond_t chan_cond(const result_t *r, const chan_cfg_t *c, uint32_t scan_no)
{
    if(c==NULL) return COND_FAULT;
    if(c->type==CH_TYPE_OFF) return COND_OFF;
    if((c->type!=CH_TYPE_K && c->type!=CH_TYPE_J) ||
       (c->mode!=CH_MODE_TRIP && c->mode!=CH_MODE_ALARM_ONLY)) return COND_FAULT;
    if(r==NULL || r->scan_no!=scan_no || r->temp_dC==TEMP_DC_INVALID ||
       r->flags!=MEAS_VALID) return COND_FAULT;
    if(r->temp_dC>c->probe_limit_dC) return COND_FAULT;
    if(r->temp_dC>=c->trip_dC) return COND_OVER_TRIP;
    if(r->temp_dC>=c->alarm_dC) return COND_OVER_ALARM;
    return COND_NORMAL;
}
act_t chan_action(cond_t cond, ch_mode_t mode)
{
    if((unsigned)cond>COND_NORMAL) return ACT_TRIP;
    if(cond==COND_OFF) return ACT_NONE;
    if(mode!=CH_MODE_TRIP && mode!=CH_MODE_ALARM_ONLY) return ACT_TRIP;
    switch(cond) {
    case COND_FAULT: case COND_OVER_TRIP: return mode==CH_MODE_TRIP?ACT_TRIP:ACT_ALARM;
    case COND_OVER_ALARM: return ACT_ALARM;
    case COND_NORMAL: case COND_OFF: return ACT_NONE;
    default: return ACT_TRIP;
    }
}
fault_code_t chan_cause(const result_t *r, cond_t cond)
{
    if(cond==COND_OVER_TRIP) return FC_C10_OVER_TRIP;
    if(cond==COND_OVER_ALARM) return FC_C11_OVER_ALARM;
    if(cond==COND_NORMAL || cond==COND_OFF) return FC_NONE;
    if(r!=NULL) {
        if(r->flags&MEAS_OPEN) return FC_C01_OPEN;
        if(r->flags&MEAS_RANGE) return FC_C02_RANGE;
        if(r->flags&MEAS_CM_FAIL) return FC_C03_COMMON_MODE;
        if(r->flags&MEAS_SHORTED) return FC_C06_SHORTED;
        if(r->flags&MEAS_OVUV) return FC_C07_OVUV;
        if(r->flags&MEAS_COLD) return FC_C08_COLD;
    }
    return FC_C02_RANGE; /* missing/stale/unknown result cannot grant RUN */
}
bool chan_trip_clear(const result_t *r, const chan_cfg_t *c, uint32_t scan_no)
{
    cond_t cond;
    if(c==NULL) return false;
    if(c->type==CH_TYPE_OFF) return true;
    if(c->mode!=CH_MODE_TRIP && c->mode!=CH_MODE_ALARM_ONLY) return false;
    if(c->mode==CH_MODE_ALARM_ONLY) return true;
    cond=chan_cond(r,c,scan_no);
    return (cond==COND_NORMAL || cond==COND_OVER_ALARM) && c->band_C>=2 && c->band_C<=50 &&
        r->temp_dC<=(int32_t)c->trip_dC-10L*c->band_C;
}
bool chan_alarm_clear(const result_t *r, const chan_cfg_t *c, uint32_t scan_no)
{
    if(c==NULL) return false;
    if(c->type==CH_TYPE_OFF) return true;
    return chan_cond(r,c,scan_no)==COND_NORMAL && c->band_C>=2 && c->band_C<=50 &&
        r->temp_dC<=(int32_t)c->alarm_dC-10L*c->band_C;
}
