#ifndef FAMILY_SETTINGS_H
#define FAMILY_SETTINGS_H
#include "common/types.h"
#include "common/fault_codes.h"
#include <stddef.h>

#define SETTINGS_SLOT_SIZE 768u
#define CAL_SLOT_SIZE 256u
#define CAL_MISSING INT32_MAX
typedef struct {
    ch_type_t type;
    ch_mode_t mode;
    char name[6];
    temp_dC_t alarm_dC, trip_dC, probe_limit_dC;
    uint8_t band_C, type_epoch;
} chan_cfg_t;
typedef struct {
    uint8_t board_type, channel_count, address, baud;
    uint16_t pin_bcd;
    uint32_t sequence;
    chan_cfg_t ch[MAX_CHANNELS];
} settings_t;
typedef struct {
    uint8_t bank_count;
    uint32_t sequence;
    int32_t ref_ppm[MAX_BANKS], baseline_nV[MAX_CHANNELS];
    uint8_t tag[MAX_CHANNELS];
} calibration_t;

/* Pure, whole-record semantic validation; no defaults or partial acceptance. */
res_t set_validate(const settings_t *s);
uint16_t set_crc16(const uint8_t *p, size_t n);
/* Slots are little endian; trailing bytes are zero; unpack checks build identity. */
res_t set_pack(const settings_t *s, uint8_t out[SETTINGS_SLOT_SIZE]);
res_t set_unpack(const uint8_t in[SETTINGS_SLOT_SIZE], uint8_t board_type,
                 uint8_t channel_count, settings_t *s);
/* -1 neither valid, 0 A, 1 B; equal/half-range sequences deterministically prefer A. */
int set_select(bool a_valid, uint32_t a_seq, bool b_valid, uint32_t b_seq);
bool set_protection_changed(const settings_t *a, const settings_t *b);
/* Edit helper: increments epoch on a change, clears limits; OFF is canonical. */
res_t set_change_type(chan_cfg_t *c, ch_type_t type);
res_t cal_validate(const calibration_t *c);
res_t cal_pack(const calibration_t *c, uint8_t out[CAL_SLOT_SIZE]);
res_t cal_unpack(const uint8_t in[CAL_SLOT_SIZE], uint8_t banks, calibration_t *c);
/* Staged records may validate but must be complete and type/epoch-bound to run. */
bool cal_complete(const calibration_t *c, const settings_t *s);
/* All-or-nothing burnout update, absolute window 1.5..10 mV. */
res_t cal_learn(calibration_t *c, const settings_t *s,
                const int32_t baseline_nV[MAX_CHANNELS]);

typedef enum { STORE_IDLE, STORE_INVALIDATE, STORE_BODY, STORE_MAGIC,
               STORE_VERIFY, STORE_DONE, STORE_FAILED } store_phase_t;
typedef enum { EE_NONE, EE_WRITE, EE_READ } ee_kind_t;
typedef struct { ee_kind_t kind; uint16_t address; uint8_t value; } ee_op_t;
typedef struct {
    store_phase_t phase;
    uint8_t image[SETTINGS_SLOT_SIZE];
    uint8_t wrap_cal_image[CAL_SLOT_SIZE];
    uint16_t length, index, base;
    uint8_t active_slot, target_slot, retries;
    bool pending, protection_change, calibration;
    bool settings_after_cal;
    uint8_t calibration_active_slot;
    bool calibration_slot_known;
    fault_code_t fault;
} set_store_t;
/* Initialize once per boot. Do not reinitialize to retry a failed commit. */
void set_store_init(set_store_t *st);
/* Begin rejects invalid RAM data; sequence is active+1. Caller must inhibit RUN
 * BEFORE executing the first emitted operation if protection_change is true.
 * active_slot = 0/1, or 2 for blank EEPROM. No settings pointer flip until STORE_DONE.
 * An in-progress transaction returns RES_BUSY; failures survive a new attempt. */
res_t set_commit(set_store_t *st, const settings_t *candidate,
                 const settings_t *active, uint8_t active_slot);
/* Required for a type-epoch wrap; plain set_commit rejects that change.
 * Copies the active calibration (valid staged records allowed; slot 0/1), clears
 * every wrapping channel's baseline/tag, and verifies its inactive A/B copy BEFORE
 * writing settings. image remains the pending settings image; calibration=true
 * during the prerequisite write. active_slot is the SETTINGS slot throughout;
 * calibration_active_slot advances after calibration verification. STORE_DONE
 * means both records verified; no caller-owned input must survive begin.
 * Retries must pass that verified slot and its calibration record; a stale
 * calibration slot is rejected. Keep this store state across attempts.
 * On reset, boot-select both A/B pairs normally. A cut can leave old settings
 * with a newly cleared baseline (requiring re-learning), never wrapped settings
 * with the ancient baseline. Non-wrapping saves follow set_commit unchanged. */
res_t set_commit_with_cal(set_store_t *st, const settings_t *candidate,
                          const settings_t *active, uint8_t active_slot,
                          const calibration_t *active_cal, uint8_t cal_slot);
/* Also rejects a stale calibration slot once this store has verified a copy. */
res_t cal_commit(set_store_t *st, const calibration_t *candidate,
                 uint32_t active_sequence, uint8_t active_slot);
/* Pure EEPROM protocol: execute op once; next call acknowledges it with ready,
 * success and (for EE_READ) value. ready=false preserves the outstanding op.
 * At most one byte request per call. Fault stays raised until successful retry. */
void set_store_step(set_store_t *st, bool ready, bool success, uint8_t value,
                    ee_op_t *op);
#endif
