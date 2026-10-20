#ifndef FAMILY_RELAYS_H
#define FAMILY_RELAYS_H
#include "common/types.h"
void relays_safe(void);
void relay_alarm(bool energise);
bool relay_run_sense(void); /* true = coil energised */
bool relay_alarm_sense(void);
#endif
