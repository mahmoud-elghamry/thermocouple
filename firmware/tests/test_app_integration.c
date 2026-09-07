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
    if (!setjmp(finished)) {
        (void)app_main_under_test();
    }
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

    run_scenario(40u, true, 1000, buttons_failed_save, temps_constant_50,
                saves_fail_once);
    CHECK(history_len >= 25u);

    /* Ten UP presses reached the edited value - proving the edit itself was
       not blocked - but it never became live. */
    CHECK(strstr(entry_at(10u)->status, "110") != NULL);

    /* The failed save inhibits running and says so explicitly, and keeps
       saying so for as long as it is unresolved. */
    for (i = 11u; i <= 20u; ++i) {
        e = entry_at(i);
        CHECK(!e->permit);
        CHECK(strstr(e->status, "SAVE FAILED") != NULL);
    }

    /* ACK is refused before a successful retry. */
    e = entry_at(21u);
    CHECK(!e->permit);
    CHECK(strstr(e->status, "SAVE FAILED") != NULL);

    /* Re-entering edit starts from the value that is actually still active -
       100, not the 110 that failed to save.  This is the direct evidence
       that the previously active setpoint was preserved (I-036). */
    e = entry_at(22u);
    CHECK(strstr(e->status, "EDIT") != NULL);
    CHECK(strstr(e->status, "100") != NULL);

    /* The retry succeeds, but running stays inhibited until it is
       acknowledged, exactly like the first-time-setup path. */
    e = entry_at(23u);
    CHECK(!e->permit);
    CHECK(strstr(e->status, "SAVE OK ACK") != NULL);

    /* Acknowledging the recovered save - and only that - clears the trip. */
    e = entry_at(24u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
}

/* --- scenario 3: simultaneous button events and a live trip --------------- */

static uint8_t buttons_simultaneous(unsigned t)
{
    if (t == 15u) {
        return (uint8_t)(HAL_BUTTON_EVENT_NEXT | HAL_BUTTON_EVENT_ACK);
    }
    if (t == 30u) return HAL_BUTTON_EVENT_ACK;
    return HAL_BUTTON_EVENT_NONE;
}
static int16_t temps_trip_then_cool(unsigned t, uint8_t ch)
{
    (void)ch;
    /* Over the 100 C setpoint, then cooled to a safe reading - by a step the
       monitor's own physical rate limit (APP_8CH_MAX_STEP_X10) still
       accepts, or the drop itself would be flagged as implausible. */
    return (t < 20u) ? 1200 : 800;
}

static void test_simultaneous_events_and_trip(void)
{
    const history_entry_t *e;

    run_scenario(40u, true, 1000, buttons_simultaneous, temps_trip_then_cool,
                NULL);
    CHECK(history_len >= 31u);

    /* NEXT and ACK arriving in the same poll are both honoured: the channel
       page changed even though the ACK in the same event was refused because
       the channel is still hot - the over-temperature trip is already
       latched by tick 15. */
    e = entry_at(15u);
    CHECK(strstr(e->channel, "CH2:") != NULL);
    CHECK(!e->permit);
    CHECK(strstr(e->status, "TRIP") != NULL);

    /* Cooling alone does not self-clear a latched trip. */
    CHECK(!entry_at(25u)->permit);

    /* Acknowledging once it is actually safe clears it. */
    e = entry_at(30u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
}

/* --- scenario 4: a healthy 0.0 C reading is not treated as invalid -------- */

static int16_t temps_all_zero(unsigned t, uint8_t ch)
{
    (void)t; (void)ch;
    return 0;
}

static void test_healthy_zero_not_rejected(void)
{
    const history_entry_t *e;

    run_scenario(25u, true, 500, NULL, temps_all_zero, NULL);
    CHECK(history_len >= 16u);

    e = entry_at(15u);
    CHECK(e->permit);
    CHECK(strstr(e->status, "SAFE") != NULL);
    CHECK(strstr(e->channel, "OK") != NULL);
    CHECK(strstr(e->channel, "+   0.0") != NULL);
}

int main(void)
{
    test_first_time_setup();
    test_failed_save_and_recovery();
    test_simultaneous_events_and_trip();
    test_healthy_zero_not_rejected();

    if (failures != 0) {
        printf("%d check(s) failed\n", failures);
        return 1;
    }
    printf("all checks passed\n");
    return 0;
}
