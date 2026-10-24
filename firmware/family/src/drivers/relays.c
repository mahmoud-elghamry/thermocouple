#include "drivers/relays.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "app/outputs_hw.h"
#include "app/timing.h"
static bool previous_pwm;
static uint16_t previous_remaining;
void relays_safe(void) { timer_run_stop(); gpio_write(board()->alarm,false); }
void relay_alarm(bool on) { gpio_write(board()->alarm,on); }
bool relay_run_sense(void) { return !gpio_read(board()->run_sense); }
bool relay_alarm_sense(void) { return !gpio_read(board()->alarm_sense); }
void outputs_hw_apply_at(bool pwm,bool alarm,uint16_t remaining,uint32_t evaluated) {
    relay_alarm(alarm);
    if(!pwm || !remaining || remaining>APP_RUN_WINDOW_MS || timer_run_expired()) { timer_run_stop(); previous_pwm=false; }
    else {
        /* OPEN-H4: shared RUN window. A new window is the only increasing countdown.
         * Repeated output servicing cannot extend the ISR deadline or restart an expired pump. */
        if(!previous_pwm || remaining>previous_remaining) (void)timer_run_start_at(remaining,evaluated);
        previous_pwm=true;
    }
    previous_remaining=remaining;
}
void outputs_hw_apply(bool pwm,bool alarm,uint16_t remaining) { outputs_hw_apply_at(pwm,alarm,remaining,tick_ms()); }
