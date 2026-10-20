/* Reuse Lane A's register models unchanged, extending only the MCAL seam.
 * Legacy driver/unit tests use its original clock. Integration enables byte
 * write latency, Timer2 during I/O, watchdog and measured bus-time accounting. */
#include "fake_hw.h"
#include "mcal/eeprom.h"
#include "mcal/timer.h"
#include "mcal/spi.h"
#include "mcal/wdt.h"
#include "drivers/keys.h"
#include "model.h"
#define fake_reset base_reset
#define fake_advance base_advance
#define timer_init base_timer_init
#define delay_us base_delay_us
#define spi_xfer base_spi_xfer
#define spi_soft_xfer base_spi_soft_xfer
#define ee_read base_ee_read
#define ee_ready base_ee_ready
#define ee_write_byte base_ee_write_byte
#define wdt_feed base_wdt_feed
#define reset_cause base_reset_cause
#define flow_check base_flow_check
#include "../fakes/fake_mcal.c"
#undef fake_reset
#undef fake_advance
#undef timer_init
#undef delay_us
#undef spi_xfer
#undef spi_soft_xfer
#undef ee_read
#undef ee_ready
#undef ee_write_byte
#undef wdt_feed
#undef reset_cause
#undef flow_check
static bool enabled,write_pending,expired,fail_eeprom;
static uint32_t clock_us,busy_until,last_feed,writes,loop_started;
static uint16_t write_address;
static uint8_t write_value,boot_cause=1;
static void advance_us(uint32_t duration) {
    uint32_t end=clock_us+duration;
    while(clock_us/1000u<end/1000u) {
        clock_us=(clock_us/1000u+1u)*1000u;
        timer_tick_isr(); keys_sample_isr();
        if(!expired && clock_us-last_feed>=250000u) { expired=true; boot_cause=8; timer_run_stop(); }
    }
    clock_us=end;
    if(write_pending && clock_us>=busy_until) {
        fake_eeprom[write_address]=write_value; write_pending=false;
    }
}
void model_enable(void) { enabled=true; }
bool model_watchdog_reset(void) { return expired; }
uint32_t model_write_count(void) { return writes; }
void model_loop_begin(void) { loop_started=clock_us; }
uint32_t model_loop_us(void) { return clock_us-loop_started; }
void model_eeprom_fail(bool fail) { fail_eeprom=fail; }
void model_power_cut(void) { write_pending=false; boot_cause=1; timer_run_stop(); }
void fake_reset(void) {
    base_reset(); clock_us=last_feed=writes=0; write_pending=expired=fail_eeprom=false; boot_cause=1;
}
void timer_init(void) {
    base_timer_init(); clock_us=last_feed=0; expired=false;
}
void fake_advance(uint32_t duration) { if(enabled) advance_us(duration*1000u); else base_advance(duration); }
void delay_us(uint16_t duration) { base_delay_us(duration); if(enabled) advance_us(duration); }
res_t spi_xfer(uint8_t tx,uint8_t *rx) {
    res_t r=base_spi_xfer(tx,rx); if(enabled) advance_us(8); return r;
}
uint8_t spi_soft_xfer(uint8_t tx) {
    uint8_t v=base_spi_soft_xfer(tx); if(enabled) advance_us(32); return v;
}
uint8_t ee_read(uint16_t address) {
    if(enabled) { advance_us(1); if(write_pending) return 0xFF; }
    return base_ee_read(address);
}
bool ee_ready(void) { return !enabled || !write_pending; }
res_t ee_write_byte(uint16_t address,uint8_t value) {
    if(!enabled) return base_ee_write_byte(address,value);
    if(address>=4096 || fail_eeprom) return RES_ERR_RANGE;
    if(write_pending) return RES_BUSY;
    write_address=address; write_value=value; busy_until=clock_us+3400u; write_pending=true; ++writes;
    return RES_OK;
}
void wdt_feed(void) { base_wdt_feed(); if(enabled) last_feed=clock_us; }
uint8_t reset_cause(void) { return enabled?boot_cause:base_reset_cause(); }
bool flow_check(uint8_t seen,uint8_t expected,uint32_t progress) {
    if(seen!=expected || tick_ms()-progress>100u) return false;
    wdt_feed(); return true;
}
