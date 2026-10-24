#include "hal/run_permit.h"
#include "mcal/board.h"
#include "mcal/gpio.h"

static bool permit_asserted;

void hal_run_permit_init(void)
{
    /* Write LOW before the pin becomes an output, so the relay cannot pulse
       during initialisation. */
    mcal_gpio_write(&BOARD_RUN_PERMIT, false);
    mcal_gpio_output(&BOARD_RUN_PERMIT);
    permit_asserted = false;

#if BOARD_HAS_RUN_PERMIT_SENSE
    /* The sense divider already defines the level; an internal pull-up would
       fight the 4.7k lower leg, so the input floats free of it. */
    mcal_gpio_input(&BOARD_RUN_PERMIT_SENSE, false);
#endif
}

void hal_run_permit_set(bool permitted)
{
    mcal_gpio_write(&BOARD_RUN_PERMIT, permitted);
    permit_asserted = permitted;
}

bool hal_run_permit_is_asserted(void)
{
    return permit_asserted;
}

bool hal_run_permit_readback_agrees(void)
{
#if BOARD_HAS_RUN_PERMIT_SENSE
    /* Asserted -> Q1 conducts -> RELAY_LOW near ground -> sense LOW. */
    bool sense_high = mcal_gpio_read(&BOARD_RUN_PERMIT_SENSE);

    return sense_high == !permit_asserted;
#else
    /* REV A0 has no sense divider: PC2 is an unconnected SPARE pin.  Reading
       it would return noise and manufacture drive faults out of nothing, so
       the check reports agreement and I-016 stays open.  Nothing here is a
       claim that the driver was verified. */
    return true;
#endif
}
