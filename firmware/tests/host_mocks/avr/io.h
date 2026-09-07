#ifndef HOST_MOCK_AVR_IO_H
#define HOST_MOCK_AVR_IO_H

/* Host stand-in for the one AVR register main_8ch.c touches directly: the
   reset-cause register it clears before enabling the watchdog. */

#include <stdint.h>

extern uint8_t MCUSR;

#endif
