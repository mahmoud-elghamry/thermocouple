#ifndef FAMILY_SERVICE_H
#define FAMILY_SERVICE_H
#include "services/settings.h"
/* Service cannot grant protection validity. Caller continues acquisition and WDT flow checks. */
void svc_init(const settings_t *cfg,calibration_t *cal,bool settings_valid,
              bool slot_a_valid,bool slot_b_valid,uint8_t cal_slot,bool flash_ok);
void svc_task(void);
bool svc_finished(void);
uint8_t svc_active_step(void); /* 0 during passive; 1..7 active */
uint32_t svc_progress_ms(void);
void svc_loop_time(uint16_t ms);
/* Refresh commissioning validity after the shared settings mailbox commits. */
void svc_settings_committed(bool valid);
/* Boot may borrow the EEPROM staging image BEFORE svc_init; saves 768 B SRAM. */
uint8_t *svc_boot_image(void);
/* Firmware boot/loop entry points (names retained from the F0 hardware seam). */
void f0_init(void);
void f0_task(void);
uint8_t f0_mode(void);
#endif
