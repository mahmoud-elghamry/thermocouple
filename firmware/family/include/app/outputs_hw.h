#ifndef FAMILY_OUTPUTS_HW_H
#define FAMILY_OUTPUTS_HW_H
#include "common/types.h"
/* Lane A seam: atomically arm Timer2 deadline before starting PWM. A zero deadline
 * always stops it. Pass remaining deadline, never reload the full RUN window from out_task. */
void outputs_hw_apply(bool pwm_enable, bool alarm_energise, uint16_t remaining_ms);
void outputs_hw_apply_at(bool pwm_enable,bool alarm_energise,uint16_t remaining_ms,uint32_t evaluated_ms);
#endif
