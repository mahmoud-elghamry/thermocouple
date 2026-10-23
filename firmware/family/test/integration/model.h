#ifndef FAMILY_INTEGRATION_MODEL_H
#define FAMILY_INTEGRATION_MODEL_H
#include <stdint.h>
#include <stdbool.h>
void model_enable(void);
void model_fast_ticks(bool enable); /* soak: collapse only identical settled ISR ticks */
void model_boot_epoch(uint32_t ms); /* test startup near wrap; never rebase live state */
void model_tc_cost(uint16_t us);
void model_cpu_us(uint16_t us);
void model_expire_on_grant(void);
bool model_watchdog_reset(void);
uint32_t model_write_count(void);
uint32_t model_settings_write_count(void);
uint32_t model_loop_us(void);
void model_loop_begin(void);
void model_eeprom_fail(bool fail);
void model_power_cut(void); /* discard the EEPROM byte still being programmed */
#endif
