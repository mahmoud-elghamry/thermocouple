#ifndef FAMILY_OUTPUTS_HW_H
#define FAMILY_OUTPUTS_HW_H
#include "common/types.h"
/* Lane A seam: atomically arm Timer2 deadline before starting PWM. A zero deadline
 * always stops it. Pass remaining deadline, never reload 900 ms from out_task. */
void outputs_hw_apply(bool pwm_enable, bool alarm_energise, uint16_t remaining_ms);
#endif
