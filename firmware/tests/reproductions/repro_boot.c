/* Historical 2026-09-29 reproduction for I-074.
 * Preserved from the review artifact; see README.md for scope and exit semantics.
 * Runs current application source, not a frozen firmware copy.
 * Not part of the default test gate; integrate the relevant scenario when fixing.
 */

#include <setjmp.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define main app_main_under_test
#include "../../src/app/main_8ch.c"
#include "mcal/board.h"
#include "mcal/spi.h"
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
    if (milliseconds == 250.0) { history_len=0u; }
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

#define CHANNELS 8u
#define REG_COUNT 128u
#define WRITE_BIT 0x80u
#define REG_LTCBH 0x0Cu

/* Real board pins carry no meaning to the model; only their identity (which
   array slot) matters, so the fields stay zeroed. */
const mcal_gpio_pin_t BOARD_SENSOR_CS_PINS[CHANNELS] = {
    {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0},
};

static uint8_t regs[CHANNELS][REG_COUNT];
static uint8_t reg_address[CHANNELS];
static bool address_phase[CHANNELS];
static int selected_channel = -1;
static bool miso_stuck;
static uint8_t miso_stuck_value;

static void reset_model(void)
{
    memset(regs, 0, sizeof(regs));
    memset(reg_address, 0, sizeof(reg_address));
    memset(address_phase, 0, sizeof(address_phase));
    selected_channel = -1;
    miso_stuck = false;
    miso_stuck_value = 0x00u;
}

static void set_channel_temperature(uint8_t channel, double celsius)
{
    long counts = (long)(celsius * 128.0);
    unsigned long reg = ((unsigned long)(counts & 0x7FFFFL) << 5) & 0xFFFFFFUL;

    regs[channel][0x0Cu] = (uint8_t)((reg >> 16) & 0xFFu);
    regs[channel][0x0Du] = (uint8_t)((reg >> 8) & 0xFFu);
    regs[channel][0x0Eu] = (uint8_t)(reg & 0xFFu);
}

void mcal_gpio_output(const mcal_gpio_pin_t *pin) { (void)pin; }

void mcal_gpio_write(const mcal_gpio_pin_t *pin, bool high)
{
    int index = (int)(pin - BOARD_SENSOR_CS_PINS);

    if (index < 0 || index >= (int)CHANNELS) {
        return;
    }
    if (!high) {
        selected_channel = index;
        address_phase[index] = true;
    } else if (selected_channel == index) {
        selected_channel = -1;
    }
}

void mcal_spi_master_init(mcal_spi_mode_t mode) { (void)mode; }

bool mcal_spi_transfer(uint8_t value, uint8_t *received)
{
    uint8_t channel;

    if (selected_channel < 0) {
        *received = 0xFFu;
        return true;
    }
    channel = (uint8_t)selected_channel;

    if (miso_stuck) {
        *received = miso_stuck_value;
        /* A stuck line still has to consume the byte, or the model's own
           address tracking desyncs once it recovers. */
        if (address_phase[channel]) {
            reg_address[channel] = value;
            address_phase[channel] = false;
        } else {
            ++reg_address[channel];
        }
        return true;
    }

    if (address_phase[channel]) {
        reg_address[channel] = value;
        address_phase[channel] = false;
        *received = 0u;
        return true;
    }
    if ((reg_address[channel] & WRITE_BIT) != 0u) {
        regs[channel][reg_address[channel] & 0x7Fu] = value;
    } else {
        *received = regs[channel][reg_address[channel] & 0x7Fu];
    }
    ++reg_address[channel];
    return true;
}


static uint8_t review_ack(unsigned t) { return t==20u ? HAL_BUTTON_EVENT_ACK : HAL_BUTTON_EVENT_NONE; }
int main(void)
{
    unsigned i;
    reset_model();
    for(i=0;i<8;i++) set_channel_temperature((uint8_t)i,20.0);
    run_scenario(32u,true,1000,review_ack,NULL,NULL);
    printf("Actual main + actual MAX31856 bank driver, healthy SPI register model at 20 C, stored SP100 C, ACK tick20\n");
    for(i=6;i<=22;i++) {
      const history_entry_t *e=entry_at(i);
      printf("tick=%u permit=%d channel='%s' status='%s'\n",i,(int)e->permit,e->channel,e->status);
    }
    CHECK(!entry_at(19)->permit);
    CHECK(strstr(entry_at(19)->status,"TRIP CH1 FAULT")!=NULL);
    CHECK(entry_at(20)->permit);
    return failures ? 1:0;
}
