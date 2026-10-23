#ifndef HAL_RUN_PERMIT_H
#define HAL_RUN_PERMIT_H

#include <stdbool.h>

/* The run-permit output: PB3 -> R30 -> Q1 gate -> K1 coil -> dry contact.
 *
 * Energised to run.  The pin is HIGH only while the unit is confident the
 * machine may run; power loss, reset, watchdog or any trip drops it and R31
 * pulls the gate to ground, so the contact opens.
 *
 * This is deliberately NOT hal/alarm_output.h.  That module drives the same
 * physical pin on the superseded single-channel board with the opposite
 * meaning - HIGH on over-temperature - and mixing the two inverts the safety
 * function silently (I-031).  The two are never linked into the same image.
 *
 * Read-back (I-016): a divider from the Q1 drain (RELAY_LOW) to PC2 tells the
 * firmware whether the driver actually followed the pin.  Asserted, the drain
 * is pulled near ground and the sense pin reads LOW; released, the coil pulls
 * it to +24 V and the sense pin reads HIGH.  A disagreement means a stuck pin,
 * an open coil or a failed transistor - the unit can no longer prove it can
 * stop the machine, so it says so instead of assuming.
 *
 * PC2 is a JTAG pin on a factory-fresh ATmega32A.  The read-back reads a
 * constant value unless JTAGEN is unprogrammed - see firmware/fuses.md.
 */

void hal_run_permit_init(void);
void hal_run_permit_set(bool permitted);
bool hal_run_permit_is_asserted(void);

/* True when the driver read-back agrees with the level last written. */
bool hal_run_permit_readback_agrees(void);

#endif
