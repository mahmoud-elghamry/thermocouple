#ifndef APP_SETTINGS_H
#define APP_SETTINGS_H

#include <stdbool.h>
#include <stdint.h>

/* The operator setpoint, held in EEPROM so it survives a power cycle.
 *
 * Before this existed the setpoint lived in RAM only: a site that set 120 degC
 * silently got 200 degC back after any reset, and the unit permitted a much
 * hotter engine than the operator had asked for (I-012).
 *
 * The record is validated on load.  An unprogrammed or corrupted EEPROM does
 * NOT fall back to a working setpoint - there is no safe guess for "how hot
 * may this engine run".  It refuses to permit running until an operator
 * stores one.  See app_protection_config_lock().
 *
 * This file is pure: the AVR EEPROM access lives in hal/settings_store.c.
 */

#define APP_SETTINGS_MAGIC 0x7B1Eu

typedef struct {
    uint16_t magic;
    int16_t setpoint_x10;
    uint16_t crc;
} app_settings_t;

/* CRC-16/CCITT-FALSE over the magic and the setpoint. */
uint16_t app_settings_crc(const app_settings_t *settings);

/* Fills in magic and crc for the given setpoint. */
void app_settings_build(app_settings_t *settings, int16_t setpoint_x10);

/* True only when the magic matches, the CRC matches and the setpoint is
   inside the configured range. */
bool app_settings_valid(const app_settings_t *settings);

#endif
