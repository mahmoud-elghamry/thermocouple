#ifndef FAMILY_AD7124_H
#define FAMILY_AD7124_H
#include "common/fault_codes.h"
#include "common/types.h"
void ad_reset_state(void);
/* Cooperative init/calibration; call each bank every loop until not BUSY. */
res_t ad_init(uint8_t bank);
/* One static register per call. OK means whole static image checked. */
res_t ad_verify(uint8_t bank);
res_t ad_verify_mutable(uint8_t bank);
res_t ad_start_slot(uint8_t bank, uint8_t slot);
res_t ad_poll(uint8_t bank, uint32_t *code);
void ad_scan_begin(uint8_t bank, uint32_t scan_no);
fault_code_t ad_fault(uint8_t bank);
uint32_t ad_errors(uint8_t bank);
uint8_t ad_id(uint8_t bank);
uint16_t ad_slot_image(uint8_t slot, uint32_t scan_no);
uint8_t ad_crc8(const uint8_t *p, uint8_t n);
res_t ad_read(uint8_t bank, uint8_t reg, uint32_t *value);
res_t ad_write(uint8_t bank, uint8_t reg, uint32_t value);
/* Diagnostic classifier preserves the first ERROR associated with a result. */
fault_code_t ad_classify_error(uint8_t slot, uint32_t error);
#endif
