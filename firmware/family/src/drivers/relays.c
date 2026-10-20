#include "drivers/relays.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "app/outputs_hw.h"
static bool previous_pwm;
static uint16_t previous_remaining;
void relays_safe(void) { timer_run_stop(); gpio_write(board()->alarm,false); }
void relay_alarm(bool on) { gpio_write(board()->alarm,on); }
bool relay_run_sense(void) { return !gpio_read(board()->run_sense); }
bool relay_alarm_sense(void) { return !gpio_read(board()->alarm_sense); }
void outputs_hw_apply(bool pwm,bool alarm,uint16_t remaining) {
    relay_alarm(alarm);
    if(!pwm || !remaining || remaining>900) { timer_run_stop(); previous_pwm=false; }
    else {
        /* OPEN-H4: 900 ms window. A new window is the only increasing countdown.
         * Repeated output servicing cannot extend the ISR deadline or restart an expired pump. */
        if(!previous_pwm || remaining>previous_remaining) timer_run_start(remaining);
        previous_pwm=true;
    }
    previous_remaining=remaining;
}
