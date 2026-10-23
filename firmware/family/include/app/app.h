#ifndef FAMILY_APP_H
#define FAMILY_APP_H
#include "app/protection.h"
/* Boot binds the single active settings/calibration and fault registry. */
void app_init(settings_t *settings, calibration_t *cal, fault_registry_t *faults,
              bool settings_valid, bool service);
/* scan has just run; immediate results first. Completion bits: 1 protection,
 * 2 outputs. SERVICE returns only bit 1; service owns its output checkpoint. */
uint8_t app_step(bool flow_ok);
res_t app_commit_settings(const settings_t *candidate); /* one-slot mailbox */
const settings_t *app_settings(void);
bool app_settings_valid(void);
const prot_state_t *app_protection(void);
const prot_out_t *app_output(void);
const fault_registry_t *app_faults(void);
const uint8_t *app_trip_bitmap(void); /* immutable view until next app pass */
ack_reason_t app_ack_reason(void); /* most recent command outcome */
uint16_t app_worst_loop_ms(void);
void app_loop_time(uint16_t ms);
#endif
