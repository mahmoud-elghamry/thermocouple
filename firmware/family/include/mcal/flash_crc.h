#ifndef FAMILY_FLASH_CRC_H
#define FAMILY_FLASH_CRC_H
#include "common/types.h"
uint16_t flash_crc_bytes(const uint8_t *data, uint16_t size);
/* Incremental far-flash CRC, 128 bytes per call; OK only on match. */
void flash_crc_begin(void);
res_t flash_crc(void);
uint16_t flash_crc_value(void); /* computed CRC, meaningful after completion */
#endif
