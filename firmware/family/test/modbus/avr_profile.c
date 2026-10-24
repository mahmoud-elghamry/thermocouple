#include "app/modbus.h"
#include <string.h>
static settings_t cfg;
static scan_out_t scan;
static prot_state_t prot;
static fault_registry_t faults;
static uint8_t request[8],pos;
static uint32_t now;
static bool pending,busy;
static bool flood;
volatile uint16_t profile_case,profile_pass,profile_errors;
void profile_begin(void) __attribute__((noinline));
void profile_end(void) __attribute__((noinline));
void profile_done(void) __attribute__((noinline));
void profile_begin(void) { __asm__ __volatile__("nop"); }
void profile_end(void) { __asm__ __volatile__("nop"); }
void profile_done(void) { __asm__ __volatile__("nop"); }
const settings_t *app_settings(void) { return &cfg; }
const scan_out_t *scan_last(void) { return &scan; }
const prot_state_t *app_protection(void) { return &prot; }
const fault_registry_t *app_faults(void) { return &faults; }
ack_reason_t app_ack_reason(void) { return ACK_NONE; }
void mb_io_configure(uint8_t code) { (void)code; }
uint32_t mb_io_now_us(void) { return now; }
bool mb_io_rx(mb_rx_t *r) {
    if(!pending || pos==(flood?16:8)) return false;
    r->byte=flood?pos:request[pos]; r->at_us=20000u+600u*pos++; r->flags=0; return true;
}
bool mb_io_tx_busy(void) { return busy; }
bool mb_io_tx_start(const uint8_t *b,uint16_t n) {
    if(n<5 || b[0]!=17) ++profile_errors;
    busy=true; return true;
}
void mb_io_status(mb_status_t *s) { memset(s,0,sizeof *s); s->schema=1; }
static void step(void) { profile_begin(); mb_task(1000); profile_end(); }
int main(void) {
    uint16_t a,count,c; uint8_t ch,kind;
    memset(&cfg,0,sizeof cfg); memset(&scan,0,sizeof scan); memset(&faults,0,sizeof faults);
    cfg.board_type=24; cfg.channel_count=24; cfg.address=17; cfg.baud=1;
    scan.scan_no=1; scan.scan_validated=true;
    for(ch=0;ch<24;ch++) {
        cfg.ch[ch].type=CH_TYPE_K; cfg.ch[ch].alarm_dC=4000; cfg.ch[ch].trip_dC=6000;
        cfg.ch[ch].probe_limit_dC=13000; scan.meas[ch].flags=MEAS_VALID; scan.meas[ch].scan_no=1;
    }
    for(kind=0;kind<2;kind++) {
        memset(faults.active,kind?0xFF:0,sizeof faults.active);
        for(a=0;a<672;a++) {
            if(a>=64 && a<100) continue;
            if(a>=340 && a<600) continue;
            count=a<64?(uint16_t)(64-a):(a<340?(uint16_t)(340-a):(uint16_t)(672-a));
            if(count>64) count=64;
            profile_case=(uint16_t)(a+1000u*kind); profile_pass=0;
            pending=busy=false; pos=0; now=0; mb_init(); step(); now=10000; step();
            request[0]=17; request[1]=3; request[2]=(uint8_t)(a>>8); request[3]=(uint8_t)a;
            request[4]=0; request[5]=(uint8_t)count; c=mb_crc16(request,6);
            request[6]=(uint8_t)c; request[7]=(uint8_t)(c>>8); pending=true; now=25000;
            step(); now=30000;
            for(profile_pass=1;profile_pass<64;profile_pass++) step();
            if(!busy) ++profile_errors;
        }
    }
    flood=true; pending=true; busy=false; now=0; mb_init(); step(); now=10000; pos=16; step();
    for(profile_pass=0;profile_pass<100;profile_pass++) {
        profile_case=2000; pos=0; now=30000; ++scan.scan_no;
        step();
    }
    profile_done(); for(;;) {}
}
