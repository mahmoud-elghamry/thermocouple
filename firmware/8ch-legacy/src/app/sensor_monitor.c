#include "app/sensor_monitor.h"
#include "app/app_config.h"

#include <stddef.h>
#include <stdint.h>

static int16_t absolute_difference(int16_t a, int16_t b)
{
    int32_t difference = (int32_t)a - (int32_t)b;

    if (difference < 0) {
        difference = -difference;
    }
    /* Readings are bounded by the MAX31856 range, so this cannot overflow. */
    return (int16_t)difference;
}

static void reset_channel(app_monitor_channel_t *channel)
{
    channel->reference_x10 = 0;
    channel->previous_x10 = 0;
    channel->scans_since_change = 0u;
    channel->primed = false;
}

void app_sensor_monitor_reset(app_sensor_monitor_t *monitor)
{
    uint8_t index;

    if (monitor == NULL) {
        return;
    }
    for (index = 0u; index < HAL_TEMPERATURE_BANK_CHANNELS; ++index) {
        reset_channel(&monitor->channel[index]);
    }
}

void app_sensor_monitor_update(app_sensor_monitor_t *monitor,
                               hal_temperature_sample_t *samples,
                               uint8_t count)
{
    uint8_t index;

    if (monitor == NULL || samples == NULL) {
        return;
    }
    if (count > HAL_TEMPERATURE_BANK_CHANNELS) {
        count = HAL_TEMPERATURE_BANK_CHANNELS;
    }

    for (index = 0u; index < count; ++index) {
        app_monitor_channel_t *channel = &monitor->channel[index];
        hal_temperature_sample_t *sample = &samples[index];
        int16_t value = sample->temperature_x10;

        /* The converter already rejected this one.  Start the history over,
           so a channel coming back from a fault is not immediately accused
           of being stuck at its first new reading. */
        if (!sample->valid) {
            reset_channel(channel);
            continue;
        }

        if (!channel->primed) {
            channel->primed = true;
            channel->reference_x10 = value;
            channel->previous_x10 = value;
            channel->scans_since_change = 0u;
            continue;
        }

        if (absolute_difference(value, channel->previous_x10) >
            APP_8CH_MAX_STEP_X10) {
            sample->faults |= HAL_TEMPERATURE_FAULT_RATE;
            sample->valid = false;
            reset_channel(channel);
            continue;
        }
        channel->previous_x10 = value;

        if (absolute_difference(value, channel->reference_x10) >=
            APP_8CH_STUCK_MIN_CHANGE_X10) {
            channel->reference_x10 = value;
            channel->scans_since_change = 0u;
            continue;
        }

        if (channel->scans_since_change < APP_8CH_STUCK_SCANS) {
            ++channel->scans_since_change;
        }
        if (channel->scans_since_change >= APP_8CH_STUCK_SCANS) {
            sample->faults |= HAL_TEMPERATURE_FAULT_STUCK;
            sample->valid = false;
        }
    }
}
