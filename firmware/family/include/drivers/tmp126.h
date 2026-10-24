#ifndef FAMILY_TMP126_H
#define FAMILY_TMP126_H
#include "common/types.h"
void cj_reset(void);
res_t cj_init(uint8_t sensor);
/* Full five-frame check, output milli-C; 0 C is a valid reading. */
res_t cj_read(uint8_t sensor, int32_t *temp_mC);
uint16_t cj_crc16(const uint8_t *p, uint8_t n);
uint16_t cj_last_id(uint8_t sensor); /* last observed ID, zero if frame was unavailable */
#endif
