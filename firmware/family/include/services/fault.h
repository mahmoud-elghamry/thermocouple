#ifndef FAMILY_FAULT_H
#define FAMILY_FAULT_H
#include "common/types.h"
#include "common/fault_codes.h"
#define FAULT_CODES 52u
#define FAULT_UNITS 96u
#define FAULT_BYTES (FAULT_UNITS / 8u)
typedef enum { ACT_NONE=0, ACT_ALARM=1, ACT_TRIP=3 } act_t;
typedef struct {
    uint8_t active[FAULT_CODES][FAULT_BYTES];
    uint8_t latch[FAULT_CODES][FAULT_BYTES];
    bool internal;
} fault_registry_t;
void fault_init(fault_registry_t *r);
/* True on a new activation; invalid codes/units raise an internal trip.
 * C-code units consumed by protection are zero-based CHANNELS (also C03).
 * Preserve raw CM pin identity separately when constructing its event. */
bool fault_raise(fault_registry_t *r, fault_code_t code, uint8_t unit);
void fault_clear(fault_registry_t *r, fault_code_t code, uint8_t unit);
bool fault_active(const fault_registry_t *r, fault_code_t code);
bool fault_at(const fault_registry_t *r, fault_code_t code, uint8_t unit);
act_t fault_action(fault_code_t code, ch_mode_t mode);
bool fault_trip_active(const fault_registry_t *r);
fault_code_t fault_first_trip(const fault_registry_t *r,uint8_t *unit); /* byte search; G/B only */
bool fault_alarm_latched(const fault_registry_t *r);
/* Settings-aware consumers combine G/B latches with fitted-channel C latches. */
bool fault_global_alarm_latched(const fault_registry_t *r);
bool fault_latched_at(const fault_registry_t *r, fault_code_t code, uint8_t unit);
/* Clears only inactive causes; internal input corruption requires reset. */
void fault_ack(fault_registry_t *r);
#endif
