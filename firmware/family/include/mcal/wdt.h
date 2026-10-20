#ifndef FAMILY_WDT_H
#define FAMILY_WDT_H
#include "common/types.h"
void wdt_init(void);
void wdt_feed(void);
uint8_t reset_cause(void);
bool fuses_ok(void);
void fuses_read(uint8_t bytes[3]);
/* Feed only after all loop checkpoints and progress within 100 ms. */
bool flow_check(uint8_t seen, uint8_t expected, uint32_t progress_ms);
#endif
