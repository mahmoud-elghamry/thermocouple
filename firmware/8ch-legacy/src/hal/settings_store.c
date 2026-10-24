#include "hal/settings_store.h"
#include "app/settings.h"

#include <avr/eeprom.h>
#include <stddef.h>
#include <string.h>

/* Address 0 of the internal EEPROM.  Nothing else in this firmware uses the
   EEPROM, so there is no allocation map to keep in step. */
static app_settings_t EEMEM stored_settings;

bool hal_settings_store_load(app_settings_t *out)
{
    if (out == NULL) {
        return false;
    }
    eeprom_busy_wait();
    eeprom_read_block(out, &stored_settings, sizeof(*out));
    return app_settings_valid(out);
}

bool hal_settings_store_save(const app_settings_t *settings)
{
    app_settings_t verify;

    if (settings == NULL || !app_settings_valid(settings)) {
        return false;
    }
    eeprom_busy_wait();
    eeprom_update_block(settings, &stored_settings, sizeof(*settings));
    eeprom_busy_wait();

    /* Read back rather than trust the write.  A worn or failing cell that
       silently refuses the new setpoint would otherwise leave the operator
       believing a limit that is not there. */
    eeprom_read_block(&verify, &stored_settings, sizeof(verify));
    return memcmp(&verify, settings, sizeof(verify)) == 0;
}
