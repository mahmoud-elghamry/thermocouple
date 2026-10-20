#ifndef FAMILY_SCAN_H
#define FAMILY_SCAN_H
#include "common/meas.h"
#include "services/settings.h"
#include "services/fault.h"
typedef struct {
    uint32_t raw[MAX_BANKS][15];
    int32_t burnout_nV[MAX_CHANNELS];
    uint16_t duration_ms;
    bool ref_test_ok, initialized;
    bool registers_ok[MAX_BANKS];
    res_t cj_status[10];
    bool cal_safe[MAX_BANKS];
} scan_diag_t;
/* Caller owns immutable settings/calibration snapshots and registry. */
void scan_init(const settings_t *cfg,const calibration_t *cal,fault_registry_t *faults);
void scan_task(void);
const scan_out_t *scan_last(void);
const scan_out_t *scan_current(void);
const scan_diag_t *scan_diagnostics(void);
uint32_t scan_progress_ms(void);
uint32_t scan_take_results(void); /* bit mask of immediate TC results since last call */
void scan_restart(void);
/* Engineering arithmetic used by scan and commissioning; integer nV. */
emf_nV_t scan_emf(uint32_t code,uint8_t gain);
fault_code_t scan_limit(uint8_t slot,uint32_t code,uint32_t partner,
                       int32_t ref_ppm,int32_t baseline_nV,uint32_t tc_code);
#endif
