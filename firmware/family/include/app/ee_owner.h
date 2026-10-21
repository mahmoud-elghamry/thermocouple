#ifndef FAMILY_EE_OWNER_H
#define FAMILY_EE_OWNER_H
#include "services/settings.h"
#include "services/events.h"
#include "services/fault.h"
/* Single EEPROM writer. Settings use the app's immutable command mailbox until
 * the transaction completes; calibration is copied here. Submit through app's
 * copy/edit/validate mailbox; do not mutate it while this owner is busy.
 * Init is boot/service-only, with no operation in flight. */
void ee_owner_init(settings_t *settings, calibration_t *cal, uint8_t settings_slot,
                   uint8_t cal_slot, bool settings_valid);
uint8_t *ee_owner_boot_image(void); /* boot-only scratch, before init */
res_t ee_owner_settings(const settings_t *candidate);
res_t ee_owner_calibration(const calibration_t *candidate);
void ee_owner_step(void); /* <= one nonblocking byte operation */
bool ee_owner_busy(void);
store_phase_t ee_owner_phase(void);
bool ee_owner_publish_pending(void);
bool ee_owner_protection_change(void);
bool ee_owner_take_begin(void);
/* 1 settings, 2 calibration, 0 none; failed transaction never publishes RAM. */
uint8_t ee_owner_take_done(void);
fault_code_t ee_owner_fault(void);
bool ee_owner_cal_saved(void);
bool ee_owner_settings_valid(void);
/* Full queue drops the NEW entry; loss is G13, never an internal trip. */
bool ee_owner_log(const event_t *event);
/* Reserve one entry; fill type/code/channel/unit/time/value/threshold before
 * returning to the loop. Owner fills sequence/cycle count; NULL counts loss. */
event_t *ee_owner_event(void);
uint32_t ee_owner_events_lost(void); /* saturating count, since owner boot init */
bool ee_owner_events_drained(void); /* includes the final byte becoming ready */
bool ee_owner_info_fault(void); /* G13 sources: save failure, I/O, event loss */
void ee_owner_ack_events(void); /* call ONLY for an accepted ACK; drain required */
void ee_owner_validated_scan(fault_code_t reset_code, uint32_t uptime_s);
uint32_t ee_owner_cycles(void);
/* Scratch writes also serialize with transactions/events; service-only. */
res_t ee_owner_scratch(uint16_t address, uint8_t value);
#endif
