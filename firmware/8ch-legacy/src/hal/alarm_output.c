#include "hal/alarm_output.h"
#include "mcal/board.h"
#include "mcal/gpio.h"

static bool alarm_on;

void hal_alarm_output_init(void)
{
    /* Write LOW before enabling the output so the relay cannot pulse at boot. */
    mcal_gpio_write(&BOARD_ALARM_OUTPUT, false);
    mcal_gpio_output(&BOARD_ALARM_OUTPUT);
    alarm_on = false;
}

void hal_alarm_output_set(bool on)
{
    mcal_gpio_write(&BOARD_ALARM_OUTPUT, on);
    alarm_on = on;
}

bool hal_alarm_output_is_on(void)
{
    return alarm_on;
}
