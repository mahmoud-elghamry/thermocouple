#ifndef FAMILY_EEPROM_H
#define FAMILY_EEPROM_H
#include "common/types.h"
/* One-byte nonblocking programming, valid addresses 0..4095. */
uint8_t ee_read(uint16_t addr);
bool ee_ready(void);
res_t ee_write_byte(uint16_t addr, uint8_t byte);
#endif
