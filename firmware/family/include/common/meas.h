/* Measurement results handed from `scan` (lane A) to `channel_eval`/`protection` (lane B).
 * Spec: 03-acquisition.md section 10, 04-protection.md section 2. Owned by Claude. */
#ifndef FAMILY_COMMON_MEAS_H
#define FAMILY_COMMON_MEAS_H

#include "common/types.h"

/* result_t.flags */
#define MEAS_VALID   0x01u /* hardware-valid (03 10.1, last paragraph) */
#define MEAS_OPEN    0x02u /* C01 open thermocouple */
#define MEAS_RANGE   0x04u /* C02 out of range */
#define MEAS_CM_FAIL 0x08u /* C03 common mode */
#define MEAS_SHORTED 0x10u /* C06 burnout lower window */
#define MEAS_OVUV    0x20u /* C07 input over/under-voltage */
#define MEAS_COLD    0x40u /* C08 implausibly cold */

typedef struct {
    temp_dC_t temp_dC;  /* TEMP_DC_INVALID when not valid */
    emf_nV_t emf_nV;
    uint32_t scan_no;   /* board scan that produced it; fresh when == current scan */
    uint8_t flags;      /* MEAS_* */
} result_t;

typedef enum { BANK_VALIDATED = 0, BANK_FAULT = 1, BANK_NOT_PRESENT = 2 } bank_status_t;

typedef struct {
    result_t meas[MAX_CHANNELS];
    bank_status_t bank[MAX_BANKS];
    temp_dC_t cj_dC[MAX_BANKS][2];
    uint32_t scan_no;
    uint32_t settings_seq;  /* settings sequence the scan was evaluated under (04 5 rule 3) */
    uint32_t completed_ms;  /* ms_tick at completion */
    bool scan_validated;    /* 03 10.2 */
} scan_out_t;

#endif
