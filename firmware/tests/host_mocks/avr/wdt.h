#ifndef HOST_MOCK_AVR_WDT_H
#define HOST_MOCK_AVR_WDT_H

/* Host stand-in for avr/wdt.h.  The watchdog is a hardware safety net with
   no host equivalent, so these are no-ops rather than fakes. */

#define WDTO_2S 2
#define wdt_disable() ((void)0)
#define wdt_enable(timeout) ((void)(timeout))
#define wdt_reset() ((void)0)

#endif
