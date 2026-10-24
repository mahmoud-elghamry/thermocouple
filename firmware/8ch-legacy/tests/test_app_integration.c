/* Host integration tests that run the real main_8ch.c against HAL doubles.
 *
 * Unlike tests/test_app_logic.c, which calls the pure modules directly, this
 * drives the actual application loop one iteration at a time and inspects
 * only what an operator could see: the two LCD lines and the run-permit
 * pin.  That is what caught I-036 and I-037 in review, and what keeps them
 * from coming back - the pure-module tests could not see either, because
 * both bugs were in how main_8ch.c wired the modules together, not in the
 * modules themselves.
 *
 * main_8ch.c is compiled in directly (its own main() renamed out of the way)
 * so this links the shipped source, not a copy of it.  The three AVR headers
 * it includes are replaced by tests/host_mocks/ - see that directory's
 * headers for what each stands in for.
 *
 * Source list: firmware/sources/host_test_app.txt
 */

#include <setjmp.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define main app_main_under_test
#include "../src/app/main_8ch.c"
#undef main

uint8_t MCUSR;

static int failures;
#define CHECK(condition)                                                     \
    do {                                                                     \
        if (!(condition)) {                                                  \
            printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #condition);      \
            ++failures;                                                      \
        }                                                                    \
    } while (0)

/* --- scenario plumbing ---------------------------------------------------- */

#define HISTORY_MAX 96u

typedef struct {
    char channel[17];
    char status[17];
    bool permit;
} history_entry_t;

static jmp_buf finished;
static unsigned tick;
static unsigned run_ticks;
static history_entry_t history[HISTORY_MAX];
static unsigned history_len;
static char pending_channel_line[17];
static bool permit_state;

static uint8_t (*button_script)(unsigned tick);
static int16_t (*temperature_script)(unsigned tick, uint8_t channel);
static bool (*save_script)(unsigned call_index);

/* While tick < invalid_until_tick every reading is reported invalid, the way
   the MAX31856 driver's first (settling) sweep is (I-074). */
static unsigned invalid_until_tick;
/* Set by a test just before run_scenario(); consumed (and cleared) by it. */
static unsigned scenario_invalid_until;

static unsigned save_calls;
static bool stored_valid;
static int16_t stored_setpoint_x10;

void host_delay_ms(double milliseconds)
{
    if (milliseconds != (double)APP_8CH_LOOP_PERIOD_MS) {
        return; /* one of the fixed boot delays, not a loop iteration */
    }
    ++tick;
    if (tick >= run_ticks) {
        longjmp(finished, 1);
    }
}

void hal_run_permit_init(void) { permit_state = false; }
void hal_run_permit_set(bool permitted) { permit_state = permitted; }
bool hal_run_permit_readback_agrees(void) { return true; }

void hal_buttons_init(void) {}
uint8_t hal_buttons_poll(void)
{
    return button_script != NULL ? button_script(tick) : HAL_BUTTON_EVENT_NONE;
}

void hal_lcd_init(void) {}
void hal_lcd_print_line(uint8_t row, const char *text)
{
    if (row == 0u) {
        snprintf(pending_channel_line, sizeof(pending_channel_line), "%s",
                 text);
        return;
    }
    if (row == 1u && history_len < HISTORY_MAX) {
        history_entry_t *entry = &history[history_len];
        snprintf(entry->status, sizeof(entry->status), "%s", text);
        snprintf(entry->channel, sizeof(entry->channel), "%s",
                 pending_channel_line);
        entry->permit = permit_state;
        ++history_len;
    }
}

bool hal_settings_store_load(app_settings_t *out)
{
    if (!stored_valid) {
        return false;
    }
    app_settings_build(out, stored_setpoint_x10);
    return true;
}

bool hal_settings_store_save(const app_settings_t *settings)
{
    ++save_calls;
    if (save_script != NULL && !save_script(save_calls)) {
        return false;
    }
    stored_valid = true;
    stored_setpoint_x10 = settings->setpoint_x10;
    return true;
}

bool hal_temperature_bank_init(void)
{
    /* Boot writes the banner and "Initializing..." to the LCD before the
       loop - and therefore before history - is meant to start.  This is
       called exactly once, right at that boundary, so it is where history
       capture actually begins. */
    history_len = 0u;
    pending_channel_line[0] = '\0';
    return true;
}
const char *hal_temperature_bank_name(void) { return "MOCK"; }
hal_temperature_sample_t hal_temperature_bank_read(uint8_t channel)
{
    hal_temperature_sample_t sample;

    sample.temperature_x10 =
        temperature_script != NULL ? temperature_script(tick, channel) : 0;
    sample.faults = HAL_TEMPERATURE_FAULT_NONE;
    sample.valid = true;
    if (tick < invalid_until_tick) {
        sample.faults = HAL_TEMPERATURE_FAULT_INIT;
        sample.valid = false;
    }
    return sample;
}

static history_entry_t empty_history_entry;

/* Bounds-checked access: an out-of-range index is a test bug, not a crash. */
static const history_entry_t *entry_at(unsigned index)
{
    if (index >= history_len) {
        printf("FAIL %s:%d  history index %u out of range (len=%u)\n",
               __FILE__, __LINE__, index, history_len);
        ++failures;
        return &empty_history_entry;
    }
    return &history[index];
}

static void run_scenario(unsigned ticks, bool eeprom_valid,
                         int16_t eeprom_setpoint_x10,
                         uint8_t (*buttons)(unsigned),
                         int16_t (*temperatures)(unsigned, uint8_t),
                         bool (*saves)(unsigned))
{
    tick = 0u;
    run_ticks = ticks;
    history_len = 0u;
    save_calls = 0u;
    stored_valid = eeprom_valid;
    stored_setpoint_x10 = eeprom_setpoint_x10;
    button_script = buttons;
    temperature_script = temperatures;
    save_script = saves;
    invalid_until_tick = scenario_invalid_until;
    scenario_invalid_until = 0u;
    if (!setjmp(finished)) {
        (void)app_main_under_test();
    }
}

/* Every power-up starts latched and needs an ACK (I-074).  Scan iterations
   are 7, 15, 23, ... (APP_8CH_SCAN_TICKS = 8), so the first valid readings
   exist from iteration 7 on.  Scenarios that begin with a healthy, stored
   setpoint ACK the power-up latch at BOOT_ACK_TICK and then run their
   original script shifted by AFTER_BOOT ticks; after_boot(n) is history
   entry n of that original script.  AFTER_BOOT is a multiple of the scan
   period so the shifted script keeps its original timing relative to the
   scans. */
#define BOOT_ACK_TICK 8u
#define AFTER_BOOT    16u

static const history_entry_t *after_boot(unsigned index)
{
    return entry_at(AFTER_BOOT + index);
}

/* --- scenario 1: first-time setup (I-037) --------------------------------- */

static uint8_t buttons_first_time(unsigned t)
{
    if (t == 0u) return HAL_BUTTON_EVENT_SET;  /* enter edit */
    if (t == 1u) return HAL_BUTTON_EVENT_UP;   /* candidate 200 -> 201 */
    if (t == 2u) return HAL_BUTTON_EVENT_SET;  /* commit: save succeeds */
    if (t == 30u) return HAL_BUTTON_EVENT_ACK; /* after it settles, ack it */
    return HAL_BUTTON_EVENT_NONE;
}
static int16_t temps_constant_20(unsigned t, uint8_t ch)
{
    (void)t; (void)ch;
    return 200; /* 20.0 C: safe against any setpoint this scenario reaches */
}

static void test_first_time_setup(void)
{
    const history_entry_t *e;

    run_scenario(45u, false, 0, buttons_first_time, temps_constant_20, NULL);
    CHECK(history_len >= 31u);

    /* Blank EEPROM: the candidate is visible while it is being entered,
       instead of the unit only saying SET SETPOINT (I-037). */
    CHECK(strstr(entry_at(0u)->status, "EDIT") != NULL);
    CHECK(strstr(entry_at(1u)->status, "201") != NULL);

    /* Save succeeds: the trip is still latched (an unacknowledged first
       setpoint is not yet a running permit) but the reason has changed from
       "unset" to "needs acknowledgement". */
    e = entry_at(2u);
    CHECK(strstr(e->status, "SAVE OK ACK") != NULL);
    CHECK(!e->permit);

    /* Once acknowledged, with a safe temperature already read, the unit
       runs and shows the setpoint it was actually given. */
    e = entry_at(30u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "201") != NULL);
    CHECK(strstr(e->status, "SAFE") != NULL);
}

/* --- scenario 2: failed save, retry, recovery ack (I-036) ----------------- */

static uint8_t buttons_failed_save(unsigned t)
{
    if (t == BOOT_ACK_TICK) return HAL_BUTTON_EVENT_ACK; /* power-up latch */
    if (t < AFTER_BOOT) return HAL_BUTTON_EVENT_NONE;
    t -= AFTER_BOOT;
    if (t == 0u) return HAL_BUTTON_EVENT_SET; /* enter edit, candidate=100 */
    if (t >= 1u && t <= 10u) return HAL_BUTTON_EVENT_UP; /* -> 110 */
    if (t == 11u) return HAL_BUTTON_EVENT_SET; /* commit: save #1 fails */
    if (t == 21u) return HAL_BUTTON_EVENT_ACK; /* rejected: not recovered */
    if (t == 22u) return HAL_BUTTON_EVENT_SET; /* re-enter: candidate=active */
    if (t == 23u) return HAL_BUTTON_EVENT_SET; /* commit: save #2 succeeds */
    if (t == 24u) return HAL_BUTTON_EVENT_ACK; /* now it clears */
    return HAL_BUTTON_EVENT_NONE;
}
static int16_t temps_constant_50(unsigned t, uint8_t ch)
{
    (void)t; (void)ch;
    return 500; /* 50.0 C: safe against both the 100 C and 110 C setpoints */
}
static bool saves_fail_once(unsigned call_index) { return call_index != 1u; }

static void test_failed_save_and_recovery(void)
{
    unsigned i;
    const history_entry_t *e;

    run_scenario(AFTER_BOOT + 40u, true, 1000, buttons_failed_save,
                 temps_constant_50, saves_fail_once);
    CHECK(history_len >= AFTER_BOOT + 25u);

    /* Ten UP presses reached the edited value - proving the edit itself was
       not blocked - but it never became live. */
    CHECK(strstr(after_boot(10u)->status, "110") != NULL);

    /* The failed save inhibits running and says so explicitly, and keeps
       saying so for as long as it is unresolved. */
    for (i = 11u; i <= 20u; ++i) {
        e = after_boot(i);
        CHECK(!e->permit);
        CHECK(strstr(e->status, "SAVE FAILED") != NULL);
    }

    /* ACK is refused before a successful retry. */
    e = after_boot(21u);
    CHECK(!e->permit);
    CHECK(strstr(e->status, "SAVE FAILED") != NULL);

    /* Re-entering edit starts from the value that is actually still active -
       100, not the 110 that failed to save.  This is the direct evidence
       that the previously active setpoint was preserved (I-036). */
    e = after_boot(22u);
    CHECK(strstr(e->status, "EDIT") != NULL);
    CHECK(strstr(e->status, "100") != NULL);

    /* The retry succeeds, but running stays inhibited until it is
       acknowledged, exactly like the first-time-setup path. */
    e = after_boot(23u);
    CHECK(!e->permit);
    CHECK(strstr(e->status, "SAVE OK ACK") != NULL);

    /* Acknowledging the recovered save - and only that - clears the trip. */
    e = after_boot(24u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
}

/* --- scenario 2b: recovered save acknowledged while hot (I-073) ----------- */

/* The same failed-save sequence as scenario 2, with a second ACK once the
   channels have cooled.  Preserved from the 2026-09-29 reproduction
   (tests/reproductions/repro_save_ack.c), where RUN_PERMIT came on at ticks
   24-30 with every channel 20 C over a 100 C limit. */
static uint8_t buttons_failed_save_then_late_ack(unsigned t)
{
    if (t == AFTER_BOOT + 42u) return HAL_BUTTON_EVENT_ACK; /* cool: accepted */
    return buttons_failed_save(t);
}
static int16_t temps_hot_during_save_fault_then_cool(unsigned t, uint8_t ch)
{
    (void)ch;
    if (t < AFTER_BOOT) return 900;
    t -= AFTER_BOOT;
    /* 90 -> 120 -> 80 C against a 100 C setpoint.  Each step is inside the
       monitor's physical rate limit (APP_8CH_MAX_STEP_X10), so neither is
       flagged as implausible: the only thing standing between the hot
       channels and RUN_PERMIT is the acknowledgement check. */
    if (t < 15u) return 900;
    if (t < 32u) return 1200;
    return 800;
}

static void test_recovered_save_ack_refused_while_hot(void)
{
    unsigned i;
    const history_entry_t *e;

    run_scenario(AFTER_BOOT + 50u, true, 1000,
                 buttons_failed_save_then_late_ack,
                 temps_hot_during_save_fault_then_cool, saves_fail_once);
    CHECK(history_len >= AFTER_BOOT + 43u);

    /* The retry succeeds while every channel is over the limit. */
    e = after_boot(23u);
    CHECK(!e->permit);
    CHECK(strstr(e->status, "SAVE OK ACK") != NULL);

    /* ACK at tick 24 is refused: the unit must not run while hot, however
       the trip was latched.  It stays off until the next accepted ACK. */
    for (i = 24u; i < 42u; ++i) {
        e = after_boot(i);
        CHECK(!e->permit);
        CHECK(strstr(e->status, "SAFE") == NULL);
    }

    /* The operator is told why, not left looking at the old save text
       (I-088).  Every channel is hot, so the first one is named; the
       message holds for as long as the channels are still hot. */
    for (i = 24u; i < 32u; ++i) {
        e = after_boot(i);
        CHECK(strcmp(e->status, "NO ACK CH1 HOT  ") == 0);
    }
    /* Once the readings are cool the message goes; the trip is still
       latched and still waiting for a new ACK. */
    e = after_boot(41u);
    CHECK(!e->permit);
    CHECK(strcmp(e->status, "SAVE OK ACK     ") == 0);

    /* Once the channels are back at or below the reset temperature, the same
       acknowledgement is accepted and the unit runs normally. */
    e = after_boot(42u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
    CHECK(strstr(e->status, "100") != NULL);
}

/* --- scenario 3: simultaneous button events and a live trip --------------- */

/* CHANGED for I-074.  Originally every channel was already hot at power-up
   and the over-temperature trip latched on the first scan.  Since I-074 a
   hot power-up is the startup latch, not a trip (see
   test_boot_with_hot_channel), so this scenario now starts cool, ACKs the
   power-up latch, and only then goes over the 100 C setpoint - which is what
   makes it a real over-temperature trip again. */
static uint8_t buttons_simultaneous(unsigned t)
{
    if (t == BOOT_ACK_TICK) return HAL_BUTTON_EVENT_ACK; /* power-up latch */
    if (t == 25u) {
        return (uint8_t)(HAL_BUTTON_EVENT_NEXT | HAL_BUTTON_EVENT_ACK);
    }
    if (t == 40u) return HAL_BUTTON_EVENT_ACK;
    return HAL_BUTTON_EVENT_NONE;
}
static int16_t temps_trip_then_cool(unsigned t, uint8_t ch)
{
    (void)ch;
    /* Cool, then over the 100 C setpoint, then cooled to a safe reading - by
       steps the monitor's own physical rate limit (APP_8CH_MAX_STEP_X10)
       still accepts, or the change itself would be flagged as implausible. */
    if (t < 12u) return 800;
    return (t < 30u) ? 1200 : 800;
}

static void test_simultaneous_events_and_trip(void)
{
    const history_entry_t *e;

    run_scenario(55u, true, 1000, buttons_simultaneous, temps_trip_then_cool,
                 NULL);
    CHECK(history_len >= 41u);

    /* The power-up ACK was accepted (cool, valid) and the unit ran. */
    CHECK(entry_at(14u)->permit);

    /* NEXT and ACK arriving in the same poll are both honoured: the channel
       page changed even though the ACK in the same event was refused because
       the channel is still hot - the over-temperature trip latched at the
       scan on tick 15. */
    e = entry_at(25u);
    CHECK(strstr(e->channel, "CH2:") != NULL);
    CHECK(!e->permit);
    CHECK(strstr(e->status, "TRIP CH1 TEMP") != NULL);

    /* Cooling alone does not self-clear a latched trip. */
    CHECK(!entry_at(35u)->permit);

    /* Acknowledging once it is actually safe clears it. */
    e = entry_at(40u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
}

/* --- scenario 4: a healthy 0.0 C reading is not treated as invalid -------- */

static int16_t temps_all_zero(unsigned t, uint8_t ch)
{
    (void)t; (void)ch;
    return 0;
}

/* CHANGED for I-074: the unit used to run with no button press once the first
   scan was done; it now needs the power-up ACK, so this scenario presses it.
   The point of the test - 0.0 C is a valid reading and is accepted - is
   unchanged. */
static uint8_t buttons_boot_ack(unsigned t)
{
    return t == BOOT_ACK_TICK ? HAL_BUTTON_EVENT_ACK : HAL_BUTTON_EVENT_NONE;
}

static void test_healthy_zero_not_rejected(void)
{
    const history_entry_t *e;

    run_scenario(25u, true, 500, buttons_boot_ack, temps_all_zero, NULL);
    CHECK(history_len >= 16u);

    /* Not running before the power-up ACK, valid 0.0 C readings or not. */
    CHECK(!entry_at(BOOT_ACK_TICK - 1u)->permit);

    e = entry_at(15u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
    CHECK(strstr(e->channel, "OK") != NULL);
    CHECK(strstr(e->channel, "+   0.0") != NULL);
}

/* --- scenario 5: every power-up waits for ACK (I-074) --------------------- */

#define START_TEXT "START: PRESS ACK"

static uint8_t buttons_ack_at_20(unsigned t)
{
    return t == 20u ? HAL_BUTTON_EVENT_ACK : HAL_BUTTON_EVENT_NONE;
}

static void test_boot_waits_for_ack(void)
{
    unsigned i;
    const history_entry_t *e;

    /* Healthy unit, stored 100 C setpoint, every channel 20 C, valid. */
    run_scenario(30u, true, 1000, buttons_ack_at_20, temps_constant_20, NULL);
    CHECK(history_len >= 26u);

    /* From the very first frame - before any scan, through the first scan
       at iteration 7 and well beyond - the output is off and the display
       says what the unit is waiting for.  Never SAFE, and no false trip. */
    for (i = 0u; i < 20u; ++i) {
        e = entry_at(i);
        CHECK(!e->permit);
        CHECK(strcmp(e->status, START_TEXT) == 0);
        CHECK(strstr(e->status, "SAFE") == NULL);
        CHECK(strstr(e->status, "TRIP") == NULL);
    }
    CHECK(strlen(entry_at(0u)->status) == 16u);

    /* The ACK is accepted (valid, 20 C <= 95 C reset temperature) and normal
       operation resumes exactly as before. */
    for (i = 20u; i < 26u; ++i) {
        e = entry_at(i);
        CHECK(e->permit);
        CHECK(strstr(e->status, "SAFE") != NULL);
        CHECK(strstr(e->status, "100") != NULL);
    }
}

/* The MAX31856 driver's first sweep is settling/invalid.  An ACK pressed
   before or during it is refused, says which channel and why, and the output
   stays off; once valid readings arrive the message clears and the next ACK
   is accepted. */
static uint8_t buttons_ack_during_settling(unsigned t)
{
    if (t == 3u) return HAL_BUTTON_EVENT_ACK;  /* before any scan */
    if (t == 10u) return HAL_BUTTON_EVENT_ACK; /* after the invalid sweep */
    if (t == 18u) return HAL_BUTTON_EVENT_ACK; /* valid readings exist */
    return HAL_BUTTON_EVENT_NONE;
}

static void test_boot_ack_refused_while_settling(void)
{
    unsigned i;
    const history_entry_t *e;

    /* Scans at iterations 7 (invalid, tick < 12), then 15 and 23 (valid). */
    scenario_invalid_until = 12u;
    run_scenario(30u, true, 1000, buttons_ack_during_settling,
                 temps_constant_20, NULL);
    CHECK(history_len >= 26u);

    for (i = 0u; i < 18u; ++i) {
        CHECK(!entry_at(i)->permit);
        CHECK(strstr(entry_at(i)->status, "SAFE") == NULL);
        CHECK(strstr(entry_at(i)->status, "TRIP") == NULL);
    }
    /* Refused before the first scan: the channels have never been read. */
    CHECK(strcmp(entry_at(3u)->status, "NO ACK CH1 FAULT") == 0);
    /* Refused after the settling sweep: still invalid, still off. */
    e = entry_at(10u);
    CHECK(!e->permit);
    CHECK(strcmp(e->status, "NO ACK CH1 FAULT") == 0);
    /* The first valid sweep (iteration 15) clears the message; the unit is
       still waiting for an ACK and still off. */
    e = entry_at(16u);
    CHECK(!e->permit);
    CHECK(strcmp(e->status, START_TEXT) == 0);
    /* ACK with valid cool readings: accepted. */
    e = entry_at(18u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
}

/* A channel already hot at power-up: ACK refused, names the channel, output
   stays off; only after it has cooled is an ACK accepted. */
static uint8_t buttons_hot_boot(unsigned t)
{
    if (t == 10u || t == 20u || t == 40u) return HAL_BUTTON_EVENT_ACK;
    return HAL_BUTTON_EVENT_NONE;
}
static int16_t temps_ch3_hot_then_cool(unsigned t, uint8_t ch)
{
    if (ch != 2u) return 200;
    return (t < 25u) ? 1200 : 800; /* 120 C then 80 C against a 100 C limit */
}

static void test_boot_with_hot_channel(void)
{
    unsigned i;
    const history_entry_t *e;

    run_scenario(50u, true, 1000, buttons_hot_boot, temps_ch3_hot_then_cool,
                 NULL);
    CHECK(history_len >= 45u);

    for (i = 0u; i < 40u; ++i) {
        CHECK(!entry_at(i)->permit);
        CHECK(strstr(entry_at(i)->status, "SAFE") == NULL);
    }
    /* Before the ACK: waiting, not tripped. */
    CHECK(strcmp(entry_at(9u)->status, START_TEXT) == 0);
    /* Refused while hot - twice - and it keeps naming the channel. */
    for (i = 10u; i < 24u; ++i) {
        CHECK(strcmp(entry_at(i)->status, "NO ACK CH3 HOT  ") == 0);
    }
    /* Cool (80 C <= 95 C) from the scan at iteration 31; the message goes. */
    CHECK(strcmp(entry_at(39u)->status, START_TEXT) == 0);
    /* ACK once cool: accepted. */
    e = entry_at(40u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
}

/* A blank EEPROM still says SET SETPOINT, and an ACK cannot clear it: the
   startup latch does not weaken the config lock. */
static void test_boot_blank_eeprom_keeps_config_lock(void)
{
    unsigned i;

    run_scenario(30u, false, 0, buttons_ack_at_20, temps_constant_20, NULL);
    CHECK(history_len >= 26u);
    for (i = 0u; i < 26u; ++i) {
        CHECK(!entry_at(i)->permit);
        CHECK(strstr(entry_at(i)->status, "SET SETPOINT") != NULL);
    }
}

int main(void)
{
    test_first_time_setup();
    test_failed_save_and_recovery();
    test_recovered_save_ack_refused_while_hot();
    test_simultaneous_events_and_trip();
    test_healthy_zero_not_rejected();
    test_boot_waits_for_ack();
    test_boot_ack_refused_while_settling();
    test_boot_with_hot_channel();
    test_boot_blank_eeprom_keeps_config_lock();

    if (failures != 0) {
        printf("%d check(s) failed\n", failures);
        return 1;
    }
    printf("all checks passed\n");
    return 0;
}
