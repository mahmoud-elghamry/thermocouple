#ifndef HOST_MOCK_UTIL_DELAY_H
#define HOST_MOCK_UTIL_DELAY_H

/* Host stand-in for util/delay.h.  _delay_ms is redirected to a function the
   test harness controls, so the main loop can be driven one iteration at a
   time instead of actually sleeping. */

void host_delay_ms(double milliseconds);
#define _delay_ms(x) host_delay_ms(x)

#endif
