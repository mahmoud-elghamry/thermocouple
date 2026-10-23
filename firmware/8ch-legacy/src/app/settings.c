#include "app/settings.h"
#include "app/app_config.h"

#include <stddef.h>
#include <stdint.h>

uint16_t app_settings_crc(const app_settings_t *settings)
{
    uint8_t payload[4];
    uint16_t crc = 0xFFFFu;
    uint8_t index;
    uint8_t bit;

    if (settings == NULL) {
        return 0u;
    }
    payload[0] = (uint8_t)(settings->magic & 0xFFu);
    payload[1] = (uint8_t)((settings->magic >> 8) & 0xFFu);
    payload[2] = (uint8_t)((uint16_t)settings->setpoint_x10 & 0xFFu);
    payload[3] = (uint8_t)(((uint16_t)settings->setpoint_x10 >> 8) & 0xFFu);

    for (index = 0u; index < 4u; ++index) {
        crc ^= (uint16_t)((uint16_t)payload[index] << 8);
        for (bit = 0u; bit < 8u; ++bit) {
            if ((crc & 0x8000u) != 0u) {
                crc = (uint16_t)((uint16_t)(crc << 1) ^ 0x1021u);
            } else {
                crc = (uint16_t)(crc << 1);
            }
        }
    }
    return crc;
}

void app_settings_build(app_settings_t *settings, int16_t setpoint_x10)
{
    if (settings == NULL) {
        return;
    }
    settings->magic = APP_SETTINGS_MAGIC;
    settings->setpoint_x10 = setpoint_x10;
    settings->crc = app_settings_crc(settings);
}

bool app_settings_valid(const app_settings_t *settings)
{
    if (settings == NULL) {
        return false;
    }
    if (settings->magic != APP_SETTINGS_MAGIC) {
        return false;
    }
    if (settings->crc != app_settings_crc(settings)) {
        return false;
    }
    /* A correct CRC over an out-of-range number is still not a setpoint this
       unit may act on. */
    if (settings->setpoint_x10 < APP_8CH_MIN_SETPOINT_X10 ||
        settings->setpoint_x10 > APP_8CH_MAX_SETPOINT_X10) {
        return false;
    }
    return true;
}
