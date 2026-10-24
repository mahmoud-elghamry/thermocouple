#include "app/outputs.h"
#include "app/outputs_hw.h"
#include <stddef.h>
void out_task(const output_decision_t *d, uint16_t window_ms)
{
    outputs_hw_apply(d!=NULL && d->pwm_enable && window_ms>0,
                     d!=NULL && d->alarm_energise,window_ms);
}
