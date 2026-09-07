#ifndef HAL_TC_DECODE_H
#define HAL_TC_DECODE_H

/* Pure decoding of the converter register images.
 *
 * These functions touch no hardware and no AVR header, so the host test
 * links them directly.  That is the whole point: a shift or a sign-extend
 * error here returns a plausible wrong temperature, the unit stays quiet,
 * and no simulation and no bench test would catch it (I-019).
 */

#include <stdbool.h>
#include <stdint.h>

/* MAX31856 linearised thermocouple temperature, registers 0x0C..0x0E.
 * 24 bits, temperature in bits [23:5], sign in bit 23, 2^-7 degC per LSB. */
int16_t tc_max31856_decode_x10(const uint8_t data[3]);

/* MAX31856 fault status register 0x0F to HAL_TEMPERATURE_FAULT_* flags. */
uint8_t tc_max31856_fault_flags(uint8_t status_register);

/* MAX6675 16-bit frame.  Temperature in bits [14:3], 0.25 degC per LSB,
 * bit 2 is the open-thermocouple flag.  Simulation only. */
int16_t tc_max6675_decode_x10(uint16_t frame);
bool tc_max6675_frame_open(uint16_t frame);

#endif
