#include "fake_hw.h"
#include "mcal/gpio.h"
#include "mcal/spi.h"
#include "mcal/timer.h"
#include "mcal/wdt.h"
#include "mcal/uart.h"
#include "mcal/eeprom.h"
#include <string.h>
#ifndef FAKE_UART_NOW
#define FAKE_UART_NOW() timer_now_us()
#endif
static uint8_t ports[4],inputs[4],ddr[4],selected;
static uint32_t ms;
static uint16_t remaining,uart_len;
static bool pump;
static uint64_t us,cs_edge;
static bool cs_seen;
static uint8_t tmp_pos,tmp_prefix;
static uart_sample_t serial_rx[64];
static uint8_t serial_head,serial_tail,serial_count,serial_baud;
static bool serial_lost,serial_busy;
static uint32_t serial_lost_at,serial_due;
static const uint8_t *serial_bytes;
static uint16_t serial_pos,serial_length;
bool fake_uart_complete;
bool fake_ref_follow;
uint8_t fake_fuses[3];
uint32_t fake_feeds,fake_bus_errors,fake_spi_bytes,fake_soft_bytes;
uint8_t fake_eeprom[4096];
char fake_uart_log[16384];
void fake_reset(void) {
    memset(ports,0,sizeof ports); memset(inputs,0xFF,sizeof inputs); memset(ddr,0,sizeof ddr);
    memset(fake_eeprom,0xFF,sizeof fake_eeprom); memset(fake_uart_log,0,sizeof fake_uart_log);
    ms=0; remaining=0; uart_len=0; pump=false; selected=255;
    fake_feeds=fake_bus_errors=fake_spi_bytes=fake_soft_bytes=0;
    us=cs_edge=0; cs_seen=false; tmp_pos=tmp_prefix=0; fake_uart_complete=true;
    serial_head=serial_tail=serial_count=0; serial_lost=serial_busy=false;
    fake_ref_follow=true;
    fake_fuses[0]=0xF7; fake_fuses[1]=0xC1; fake_fuses[2]=0xFC;
    fake_ad_reset(); fake_tmp_reset(); inputs[0]&=0xFB;
}
void gpio_init(void) {
    memcpy(ports,board()->port_init,4); memcpy(ddr,board()->ddr_init,4);
}
void gpio_write(pin_t p,bool high) {
    uint8_t b,i; bool old=(ports[p>>3]&(1u<<(p&7)))!=0;
    if(high) ports[p>>3]|=(uint8_t)(1u<<(p&7)); else ports[p>>3]&=(uint8_t)~(1u<<(p&7));
    if(old==high) return;
    for(b=0;b<board()->banks;b++) if(p==board()->adc_cs[b]) {
        if(cs_seen && us-cs_edge<1) ++fake_bus_errors; cs_edge=us; cs_seen=true;
        if(!high) { if(selected!=255) ++fake_bus_errors; selected=b; fake_ad_select(b); }
        else { fake_ad_end(); selected=255; }
    }
    for(i=0;i<board()->cj_count;i++) if(p==board()->cj_cs[i]) {
        if(cs_seen && us-cs_edge<1) ++fake_bus_errors; cs_edge=us; cs_seen=true;
        if(!high) { if(selected!=255) ++fake_bus_errors; selected=(uint8_t)(6+i); tmp_pos=0; fake_tmp_select(i); }
        else { fake_tmp_end(); selected=255; }
    }
    if(p==board()->sio_wr_n && !high && selected<6) ++fake_bus_errors;
    if(p==board()->reftest && fake_ref_follow) fake_pin(board()->refok,high);
    if(p==board()->alarm) fake_pin(board()->alarm_sense,!high);
}
bool gpio_read(pin_t p) { return (inputs[p>>3]&(1u<<(p&7)))!=0; }
void gpio_mask(uint8_t p,uint8_t m,uint8_t v) { ports[p]=(uint8_t)((ports[p]&(uint8_t)~m)|(v&m)); }
void fake_pin(pin_t p,bool h) {
    if(h) inputs[p>>3]|=(uint8_t)(1u<<(p&7)); else inputs[p>>3]&=(uint8_t)~(1u<<(p&7));
}
uint8_t fake_port(uint8_t p) { return ports[p]; }
uint8_t fake_ddr(uint8_t p) { return ddr[p]; }
void delay_us(uint16_t delay) { us+=delay; }
void spi_init(void) { }
void spi_enable(bool e) { (void)e; }
res_t spi_xfer(uint8_t tx,uint8_t *rx) {
    ++fake_spi_bytes; if(selected>=6) return RES_ERR_TIMEOUT;
    if(us-cs_edge<1 || !(ports[board()->sio_wr_n>>3]&(1u<<(board()->sio_wr_n&7)))) ++fake_bus_errors;
    *rx=fake_ad_byte(tx); us+=8; return RES_OK;
}
uint8_t spi_soft_xfer(uint8_t tx) {
    ++fake_soft_bytes;
    if(selected<6 || selected>=16) { ++fake_bus_errors; return 0xFF; }
    if(tmp_pos==0) tmp_prefix=tx;
    if(((ports[board()->sio_wr_n>>3]&(1u<<(board()->sio_wr_n&7)))!=0) != (tmp_pos>=2 && (tmp_prefix&1)!=0)) ++fake_bus_errors;
    ++tmp_pos; us+=32;
    return fake_tmp_byte(tx);
}
void timer_init(void) { ms=0; remaining=0; pump=false; }
uint32_t tick_ms(void) { return ms; }
void timer_tick_isr(void) { ++ms; us+=1000; if(remaining && --remaining==0) timer_run_stop(); }
void fake_advance(uint32_t dt) { uint32_t i; for(i=0;i<dt;i++) { timer_tick_isr(); fake_uart_step(tick_ms()*1000u); } }
void timer_run_start(uint16_t d) { remaining=d<=1000?d:0; pump=remaining!=0; fake_pin(board()->run_sense,!pump); }
void timer_run_stop(void) { remaining=0; pump=false; gpio_write(board()->run,false); fake_pin(board()->run_sense,true); }
void timer_run_static_high(void) { timer_run_stop(); gpio_write(board()->run,true); remaining=1000; }
uint16_t timer_run_remaining(void) { return remaining; }
bool timer_run_active(void) { return pump; }
void wdt_init(void) { }
void wdt_feed(void) { ++fake_feeds; }
uint8_t reset_cause(void) { return 1; }
void fuses_read(uint8_t f[3]) { memcpy(f,fake_fuses,3); }
bool fuses_ok(void) { return fake_fuses[0]==0xF7 && fake_fuses[1]==0xC1 && (fake_fuses[2]&7)==4; }
bool flow_check(uint8_t s,uint8_t e,uint32_t p) { if(s!=e || tick_ms()-p>100) return false; wdt_feed(); return true; }
uint8_t ee_read(uint16_t a) { return a<4096?fake_eeprom[a]:0xFF; }
bool ee_ready(void) { return true; }
res_t ee_write_byte(uint16_t a,uint8_t v) { if(a>=4096) return RES_ERR_RANGE; fake_eeprom[a]=v; return RES_OK; }
void uart_init(void) { serial_head=serial_tail=serial_count=0; serial_lost=serial_busy=false; }
bool uart_put(uint8_t b) { if(uart_len>=sizeof fake_uart_log-1) return false; fake_uart_log[uart_len++]=(char)b; return true; }
bool uart_get(uint8_t *b) { (void)b; return false; }
bool uart_tx_complete(void) { return fake_uart_complete; }
void uart_rx_isr(uint8_t b) { (void)b; }
void uart_tx_isr(void) { }
uint32_t timer_now_us(void) { return tick_ms()*1000u; }
void fake_uart_clear(void) { uart_len=0; memset(fake_uart_log,0,sizeof fake_uart_log); }
uint16_t fake_uart_tx_size(void) { return uart_len; }
uint8_t fake_uart_rx_count(void) { return serial_count; }
void uart_configure_rtu(uint8_t baud) {
    serial_head=serial_tail=serial_count=0; serial_lost=serial_busy=false; serial_baud=baud;
    gpio_write(board()->de,false);
}
void fake_uart_receive(uint8_t byte,uint8_t error) {
    uart_sample_t *s;
    if(serial_busy) return;
    if(serial_count==64) { serial_head=serial_tail=serial_count=0; serial_lost=true; serial_lost_at=FAKE_UART_NOW(); return; }
    s=&serial_rx[serial_head]; s->byte=byte; s->flags=error?1:0; s->at_us=FAKE_UART_NOW();
    serial_head=(uint8_t)((serial_head+1u)&63u); ++serial_count;
}
bool uart_rx_sample(uart_sample_t *s) {
    if(serial_lost) { s->at_us=serial_lost_at; s->byte=0; s->flags=1; serial_lost=false; return true; }
    if(!serial_count) return false;
    *s=serial_rx[serial_tail]; serial_tail=(uint8_t)((serial_tail+1u)&63u); --serial_count; return true;
}
bool uart_binary_start(const uint8_t *p,uint16_t n) {
    if(!p || !n || n>256 || serial_busy || serial_count || serial_lost) return false;
    serial_bytes=p; serial_length=n; serial_pos=0; serial_busy=true;
    serial_due=FAKE_UART_NOW()+(serial_baud?573u:1146u); gpio_write(board()->de,true); return true;
}
bool uart_binary_busy(void) { return serial_busy; }
void fake_uart_step(uint32_t now) {
    uint16_t i;
    for(i=0;i<256 && serial_busy && (int32_t)(now-serial_due)>=0;i++) {
        if(uart_len<sizeof fake_uart_log) fake_uart_log[uart_len++]=(char)serial_bytes[serial_pos];
        serial_due+=serial_baud?573u:1146u;
        if(++serial_pos==serial_length) { serial_busy=false; gpio_write(board()->de,false); }
    }
}
