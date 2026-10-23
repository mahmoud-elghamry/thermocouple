#ifndef FAMILY_PROTECTION_H
#define FAMILY_PROTECTION_H
#include "app/channel_eval.h"
typedef enum { CONFIG_LOCK=0, START_LATCHED=1, RUN=2, TRIPPED=3, SERVICE=4 } prot_mode_t;
typedef enum { ACK_NONE=0, ACK_R1_RELEASE, ACK_R2_SCAN, ACK_R3_FAULT,
               ACK_R4_CHANNEL, ACK_R5_SETTINGS, ACK_R6_RELAY } ack_reason_t;
typedef struct {
    bool valid;
    fault_code_t code;
    uint8_t channel, unit;
    temp_dC_t value_dC, threshold_dC;
    uint32_t uptime_s;
} first_out_t;
typedef struct {
    prot_mode_t mode;
    uint8_t mode_inv, permit, permit_inv;
    bool ack_released, window_valid;
    uint32_t window_started_ms;
    uint32_t accepted_settings_seq, replaced_settings_seq;
    bool replaced_sequence_valid;
    /* Last validated configuration observed by step/result; unknown is fitted. */
    uint8_t fitted[(MAX_CHANNELS+7u)/8u];
    uint8_t alarm_latch[MAX_CHANNELS];
    uint8_t trip_seen[MAX_CHANNELS];
    uint32_t latest_scan[MAX_CHANNELS];
    temp_dC_t latest_temp[MAX_CHANNELS]; /* first-out on a refused startup ACK */
    uint8_t latest_seen[(MAX_CHANNELS+7u)/8u];
    uint8_t alarm_clear[(MAX_CHANNELS+7u)/8u],trip_clear[(MAX_CHANNELS+7u)/8u];
    uint8_t completed_clear[(MAX_CHANNELS+7u)/8u];
    uint32_t clear_scan,clear_settings;
    bool clear_valid;
    const settings_t *pass_cfg;
    bool pass_prepared,pass_valid;
    first_out_t first;
} prot_state_t;
typedef struct {
    const settings_t *settings;
    const scan_out_t *scan;
    fault_registry_t *faults;
    uint32_t now_ms, uptime_s;
    bool settings_valid, calibration_valid, writing;
    bool scan_complete, ack, ack_key_released;
    /* Optional shell evidence: results_evaluated certifies EVERY completed
     * result was already passed to prot_on_result unchanged; scan_unchanged
     * certifies the immutable completed snapshot/configuration is unchanged.
     * Standalone callers leave both false. Neither relaxes ACK evidence. */
    bool results_evaluated,scan_unchanged;
    uint16_t ack_held_ms, ack_age_ms;
    bool readback_off_ok, flow_ok;
    /* Begin protection edit before EEPROM I/O; completed commit unlocks CONFIG_LOCK. */
    bool commit_begin, commit_done, protection_change;
} prot_in_t;
typedef struct {
    bool run_permission, alarm_active, window_refresh;
    uint16_t window_remaining_ms;
    ack_reason_t ack_reason;
    uint8_t refusal_channel;
    uint16_t event_mask; /* bit (event_type - 1); transition notifications */
} prot_out_t;
/* Caller owns all state. Service takes precedence over missing settings at boot. */
void prot_init(prot_state_t *s, bool settings_ok, bool cal_ok, bool service);
bool prot_integrity(const prot_state_t *s);
/* Once per shell pass; configuration stays immutable until prot_step returns.
 * Standalone callers need not prepare: prot_on_result still validates itself. */
bool prot_begin_pass(prot_state_t *s,const settings_t *cfg);
/* Immediate calls: never wait for scan completion. New causes returned for logging.
 * Publish the active configuration via step/result before C-fault notifications;
 * their zero-based unit is checked against its fitted mask (channel is event ID). */
bool prot_on_result(prot_state_t *s, uint8_t ch, const result_t *r,
                    const settings_t *cfg, uint32_t scan_no, uint32_t uptime_s);
bool prot_on_fault(prot_state_t *s, fault_registry_t *reg, fault_code_t code,
                   uint8_t unit, ch_mode_t mode, uint8_t channel, uint32_t uptime_s);
/* Shell has already raised this newly active registry bit. Returns its action;
 * skips a duplicate registry write, retaining the same protection notification. */
act_t prot_observe_fault(prot_state_t *s,fault_registry_t *reg,fault_code_t code,
    uint8_t unit,ch_mode_t mode,uint8_t channel,uint32_t uptime_s);
void prot_step(const prot_in_t *in, prot_state_t *s, prot_out_t *out);
#endif
