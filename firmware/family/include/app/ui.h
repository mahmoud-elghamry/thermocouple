#ifndef FAMILY_UI_H
#define FAMILY_UI_H
#include "app/app.h"
#include "services/events.h"
#include "drivers/keys.h"

/* Standalone 24-channel operator UI. Call after app_init; no hardware init,
 * EEPROM access, protection decisions or ACK handling is performed here. */
void ui_init(void);
/* Bind the app's existing settings mailbox (no additional RAM allocation).
 * It must be exclusively available to UI preparation until app_commit_settings
 * accepts it, and immutable thereafter until ui_store_result. Bind after init.
 * app_commit_settings must skip its copy when candidate == &mailbox. */
void ui_bind_candidate(settings_t *mailbox);
/* budget_us: 0 does no work; >=1000 permits one bounded step. LCD transport
 * remains the caller's lcd_task(). Never call both service UI and this UI. */
void ui_task(uint16_t budget_us);
/* Route non-ACK events here from the single key dispatcher. False = pending
 * event already occupied, or ACK/NONE (ACK belongs to protection). */
bool ui_key(key_t key);
/* App reports every completed ACK command, including repeated equal refusals.
 * This refreshes the 3-second message and never submits/accepts an ACK. */
void ui_ack_result(ack_reason_t reason);
/* Owner calls once for the accepted transaction's final durable outcome.
 * RES_BUSY is not completion. Mailbox acceptance alone never shows SAVED OK. */
void ui_store_result(res_t result);
/* Boot calls after detecting ACK+SET at 300 ms, before keys_rearm(). The
 * special reset command must be executed/logged by app, even on blank settings.
 * ui_take_pin_reset is consumed once; app replies through ui_store_result. */
void ui_pin_recovery(void);
bool ui_take_pin_reset(void);
/* Read-only event seam: poll age (0=newest); supply the matching age and count
 * 0..32 after nonblocking owner I/O. ERR_CRC displays --; no EEPROM UI reads. */
uint8_t ui_event_age(void);
bool ui_event_request(uint8_t *age); /* true until this age has a final reply */
void ui_event_result(uint8_t age, uint8_t count, res_t result, const event_t *e);
/* Detail MIN/MAX since accepted ACK and position-compensated CJ come from the
 * acquisition/app snapshot owner. Values are 0.1 C, INVALID means unavailable. */
uint8_t ui_channel(void); /* zero based, currently selected channel */
void ui_detail_stats(temp_dC_t minimum, temp_dC_t maximum, temp_dC_t cj);
void ui_service_step(const char step[4]);
/* App/event owner supplies newest active/latched cause and aggregate count;
 * deriving "newest" from channel number would be incorrect. channel is 1..24
 * or 0 for a global/bank cause; bank unit is zero based. */
void ui_alarm_snapshot(uint8_t count, fault_code_t code, uint8_t channel, uint8_t unit);

/* Shared renderer/editor representation; compact working copy, no invented
 * protection limits. These types also allow pure screen tests on the host. */
#define UI_CHANNELS 24u
typedef enum { UI_HOME, UI_SELECT, UI_DETAIL, UI_EVENTS, UI_PIN, UI_SETUP,
    UI_CHANNELS_MENU, UI_FIELDS, UI_EDIT, UI_COMMS, UI_NEW_PIN, UI_CONFIRM,
    UI_SAVING, UI_RECOVER } ui_screen_t;
typedef enum { UF_TYPE, UF_MODE, UF_NAME, UF_ALARM, UF_TRIP, UF_BAND,
    UF_LIMIT, UF_ADDRESS, UF_BAUD, UF_PIN } ui_field_t;
typedef enum { UM_NONE, UM_BAD_PIN, UM_LOCKOUT, UM_PIN_MISMATCH, UM_NEW_PIN,
    UM_INVALID, UM_ORDER, UM_REENTER, UM_BUSY, UM_FAILED_PROT, UM_FAILED_INFO,
    UM_SAVED, UM_SAVED_ACK, UM_STALE, UM_OFF, UM_RANGE,
    UM_R1, UM_R2, UM_R3, UM_R4, UM_R5, UM_R6 } ui_message_t;
typedef struct {
    int16_t alarm, trip, limit;
    char name[6];
    uint8_t type, mode, band, epoch;
} ui_chan_t;
typedef struct {
    ui_chan_t work[UI_CHANNELS];
    event_t event;
    uint32_t activity_ms, message_ms, lock_ms, base_sequence;
    temp_dC_t minimum, maximum, cj;
    int16_t edit_value;
    uint16_t pin, pin_first, work_pin;
    ui_screen_t screen;
    ui_field_t field;
    ui_message_t message;
    key_t pending;
    ack_reason_t ack_seen;
    prot_mode_t previous_mode;
    uint8_t page, channel, item, position, digit, attempts, address, baud;
    uint8_t diff, event_age, event_count, entry_mask;
    uint8_t alarm_count, alarm_channel, alarm_unit;
    fault_code_t alarm_code;
    bool session, blank, pin_second, protection_change, reset_pending;
    bool recovering, event_valid, locked, transaction, alarm_snapshot, event_requested;
    char edit_name[6], service_step[4];
} ui_state_t;
typedef struct {
    const settings_t *settings;
    const prot_state_t *protection;
    const prot_out_t *output;
    const fault_registry_t *faults;
    const scan_out_t *scan;
    uint32_t now_ms;
} ui_snapshot_t;
/* Pure: write exactly 20/80 space-padded characters, no terminating NUL. */
void ui_render_row(const ui_state_t *u, const ui_snapshot_t *s, uint8_t row, char out[20]);
void ui_render(const ui_state_t *u, const ui_snapshot_t *s, char out[80]);

/* Module-internal seams, shared by the small ui*.c translation units. */
void ui_begin(ui_state_t *u, const settings_t *s, bool blank);
void ui_edit_begin(ui_state_t *u);
void ui_edit_key(ui_state_t *u, key_t key);
bool ui_find_diff(ui_state_t *u, const settings_t *s, int8_t direction);
/* One preparation step: clear 64 bytes, copy two channels, or validate whole
 * candidate. RES_BUSY means more steps; RES_OK means ready for mailbox submit. */
res_t ui_prepare(ui_state_t *u, const settings_t *s, settings_t *candidate);
void ui_number(char *out, uint8_t width, int32_t value, bool zero);
int16_t ui_whole(int16_t dC);
void ui_text(char *out, uint8_t offset, const char *text);
void ui_name(char out[6], const char name[6]); /* space-fill invalid/blank bytes */
#ifdef __AVR__
#include <avr/pgmspace.h>
#define UI_STR(s) PSTR(s)
/* avr-gcc otherwise moves switch result tables (including flash string
 * pointers) into SRAM. Dispatch tables belong in flash on this target. */
#define UI_NO_RAM_TABLE __attribute__((optimize("no-tree-switch-conversion")))
#else
#define UI_STR(s) (s)
#define UI_NO_RAM_TABLE
#endif
#endif
