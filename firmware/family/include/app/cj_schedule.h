#ifndef FAMILY_CJ_SCHEDULE_H
#define FAMILY_CJ_SCHEDULE_H
#include "common/types.h"
/* One CRC-protected register frame per call; RES_BUSY until this sensor's
 * status, temperature, identity, configuration and signature are all fresh. */
res_t cj_read_step(uint8_t sensor,int32_t *temperature_mC);
#endif
