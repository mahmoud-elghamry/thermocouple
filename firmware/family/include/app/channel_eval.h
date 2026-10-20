#ifndef FAMILY_CHANNEL_EVAL_H
#define FAMILY_CHANNEL_EVAL_H
#include "common/meas.h"
#include "services/settings.h"
#include "services/fault.h"
typedef enum { COND_OFF, COND_FAULT, COND_OVER_TRIP, COND_OVER_ALARM, COND_NORMAL } cond_t;
/* Freshness is explicit; stale data never passes a protection comparison. */
cond_t chan_cond(const result_t *r, const chan_cfg_t *c, uint32_t scan_no);
act_t chan_action(cond_t cond, ch_mode_t mode);
fault_code_t chan_cause(const result_t *r, cond_t cond);
bool chan_trip_clear(const result_t *r, const chan_cfg_t *c, uint32_t scan_no);
bool chan_alarm_clear(const result_t *r, const chan_cfg_t *c, uint32_t scan_no);
#endif
