#include "hal/tc_decode.h"
#include "hal/temperature_sensor.h"

#include <stdint.h>

#define MAX31856_FAULT_OPEN     0x01u
#define MAX31856_FAULT_OVUV     0x02u
#define MAX31856_FAULT_TCLOW    0x04u
#define MAX31856_FAULT_TCHIGH   0x08u
#define MAX31856_FAULT_CJLOW    0x10u
#define MAX31856_FAULT_CJHIGH   0x20u
#define MAX31856_FAULT_TCRANGE  0x40u
#define MAX31856_FAULT_CJRANGE  0x80u

int16_t tc_max31856_decode_x10(const uint8_t data[3])
{
    int32_t raw;

    raw = (int32_t)data[0] << 16;
    raw |= (int32_t)data[1] << 8;
    raw |= (int32_t)data[2];

    /* Sign-extend the 24-bit register before shifting, so a negative
       temperature stays negative through the arithmetic shift below. */
    if ((raw & 0x00800000L) != 0) {
        raw |= (int32_t)0xFF000000L;
    }
    raw >>= 5;

    /* 2^-7 degC per LSB -> tenths of a degree. */
    return (int16_t)((raw * 10L) / 128L);
}

uint8_t tc_max31856_fault_flags(uint8_t status_register)
{
    uint8_t flags = HAL_TEMPERATURE_FAULT_NONE;

    if ((status_register & MAX31856_FAULT_OPEN) != 0u) {
        flags |= HAL_TEMPERATURE_FAULT_OPEN;
    }
    if ((status_register & MAX31856_FAULT_OVUV) != 0u) {
        flags |= HAL_TEMPERATURE_FAULT_VOLTAGE;
    }
    if ((status_register &
         (MAX31856_FAULT_TCRANGE | MAX31856_FAULT_CJRANGE)) != 0u) {
        flags |= HAL_TEMPERATURE_FAULT_RANGE;
    }
    if ((status_register &
         (MAX31856_FAULT_TCHIGH | MAX31856_FAULT_CJHIGH |
          MAX31856_FAULT_TCLOW | MAX31856_FAULT_CJLOW)) != 0u) {
        flags |= HAL_TEMPERATURE_FAULT_THRESHOLD;
    }
    return flags;
}

int16_t tc_max6675_decode_x10(uint16_t frame)
{
    uint16_t counts = (uint16_t)((frame & 0x7FF8u) >> 3);

    /* 0.25 degC per LSB -> tenths of a degree.  The MAX6675 has no
       negative range, so no sign handling is needed. */
    return (int16_t)(((uint32_t)counts * 10u) / 4u);
}

bool tc_max6675_frame_open(uint16_t frame)
{
    return (frame & (uint16_t)(1u << 2)) != 0u;
}
