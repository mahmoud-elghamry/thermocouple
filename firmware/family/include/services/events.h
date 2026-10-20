#ifndef FAMILY_EVENTS_H
#define FAMILY_EVENTS_H
#include "common/types.h"
#include "common/fault_codes.h"
#define EVENT_SLOTS 32u
typedef enum { EV_POWER_UP=1, EV_TRIP, EV_ALARM, EV_FAULT, EV_ACK,
               EV_SETTINGS_CHANGED, EV_NAME_CHANGED, EV_SERVICE_ENTRY,
               EV_CALIBRATION, EV_PIN_RESET } event_type_t;
typedef struct {
    uint16_t sequence, power_cycles;
    event_type_t type;
    fault_code_t code;
    uint8_t channel, unit;
    uint32_t uptime_s;
    temp_dC_t value_dC, threshold_dC;
} event_t;
typedef struct { uint8_t slot[EVENT_SLOTS][16]; } events_t;
uint8_t ev_crc8(const uint8_t *p, uint8_t n);
res_t ev_pack(const event_t *e, uint8_t out[16]);
res_t ev_unpack(const uint8_t in[16], event_t *e);
/* Return physical newest slot, or -1 if none; CRC failures are skipped. */
int ev_newest(const events_t *r);
/* Pure RAM ring; caller persists the returned physical slot, one entry per transition. */
int ev_log(events_t *r, const event_t *e);
res_t ev_get(const events_t *r, uint8_t age, event_t *e);
#endif
