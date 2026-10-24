#ifndef HAL_SETTINGS_STORE_H
#define HAL_SETTINGS_STORE_H

#include "app/settings.h"

#include <stdbool.h>

/* Non-volatile home of the operator setpoint (I-012).
 *
 * The EEPROM survives a chip erase only while the EESAVE fuse is programmed;
 * see firmware/fuses.md.  Without it, reprogramming the unit silently wipes
 * the setpoint and the unit comes back config-locked - safe, but the site has
 * to set it again and should be told why.
 */

/* True when a validated record was read.  On false, out holds an invalid
   record and the caller must config-lock. */
bool hal_settings_store_load(app_settings_t *out);

/* Writes and reads back.  False means the setpoint is not safely stored, so
   the caller must not treat it as persisted. */
bool hal_settings_store_save(const app_settings_t *settings);

#endif
