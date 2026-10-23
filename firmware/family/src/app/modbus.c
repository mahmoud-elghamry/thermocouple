#include "app/modbus.h"
#include "services/scan.h"
#include <string.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
#define FLASH PROGMEM
#define NIBBLE(i) pgm_read_word(&crc_table[i])
#else
#define FLASH
#define NIBBLE(i) crc_table[i]
#endif
#define RX_STEP 8u
static const uint16_t crc_table[16] FLASH={
    0x0000,0xCC01,0xD801,0x1400,0xF001,0x3C00,0x2800,0xE401,
    0xA001,0x6C00,0x7800,0xB401,0x5000,0x9C01,0x8801,0x4400
};
static uint16_t crc_byte(uint16_t c,uint8_t byte) {
    c^=byte; c=(uint16_t)((c>>4)^NIBBLE(c&15u));
    return (uint16_t)((c>>4)^NIBBLE(c&15u));
}
uint16_t mb_crc16(const uint8_t *p,uint16_t n) {
    uint16_t c=0xFFFF;
    while(n--) c=crc_byte(c,*p++);
    return c;
}
/* Internal pure primitives; no I/O, no retained state. */
uint16_t mb_prepare(const mb_snapshot_t *,const uint8_t *,uint16_t,uint8_t *,uint16_t,uint16_t *);
uint16_t mb_register(const mb_snapshot_t *,uint16_t);
uint8_t mb_channel_state(const mb_snapshot_t *,uint8_t);
static uint8_t buffer[MB_TX_BYTES]; /* RX and TX share storage, never concurrent */
static uint16_t age[MAX_CHANNELS],length,rx_crc,tx_crc,tx_length,tx_pos;
static uint32_t last_rx,last_scan,last_validated;
static uint8_t address,baud_code;
static bool configured,receiving,bad,resync,tx_owned,have_validated;
static mb_snapshot_t work;
static mb_map_cache_t cache;
static first_out_t epoch_first;
static uint8_t epoch_alarm[MAX_CHANNELS],build_index,phase;
static uint32_t epoch_revision,epoch_scan,epoch_settings;
static prot_mode_t epoch_mode;
static bool epoch_internal;
static uint16_t start_register;

void mb_init(void) {
    uint8_t ch;
    for(ch=0;ch<MAX_CHANNELS;ch++) age[ch]=UINT16_MAX;
    length=tx_length=tx_pos=0; rx_crc=tx_crc=0xFFFF;
    last_rx=last_scan=last_validated=0; address=baud_code=0;
    configured=receiving=bad=tx_owned=have_validated=false; resync=true;
    phase=0;
}
static void history(const settings_t *cfg,const scan_out_t *scan) {
    uint8_t ch; uint32_t delta;
    if(scan->scan_no==last_scan) return;
    delta=scan->scan_no-last_scan;
    /* Restarted scan or a very large interval cannot make old data younger. */
    if(delta>UINT16_MAX) delta=UINT16_MAX;
    for(ch=0;ch<cfg->channel_count && ch<MAX_CHANNELS;ch++) {
        const result_t *r=&scan->meas[ch];
        if(scan->settings_seq==cfg->sequence && r->scan_no==scan->scan_no &&
           r->flags==MEAS_VALID && r->temp_dC!=TEMP_DC_INVALID) age[ch]=0;
        else if(delta>=(uint32_t)(UINT16_MAX-age[ch])) age[ch]=UINT16_MAX;
        else age[ch]=(uint16_t)(age[ch]+delta);
    }
    last_scan=scan->scan_no;
    if(scan->scan_validated) { have_validated=true; last_validated=scan->completed_ms; }
}
static void respond(const settings_t *cfg,const scan_out_t *scan) {
    if(bad || length<4 || rx_crc!=0) return;
    work.settings=cfg; work.scan=scan; work.protection=app_protection(); work.faults=app_faults(); work.age=age;
    mb_io_status(&work.status); work.ack_reason=app_ack_reason(); work.cache=NULL;
    work.have_validated=have_validated; work.last_validated_ms=last_validated;
    tx_length=mb_prepare(&work,buffer,length,buffer,sizeof buffer,&start_register);
    tx_pos=0; tx_crc=0xFFFF;
    if(!tx_length) return;
    epoch_settings=cfg->sequence; epoch_scan=scan->scan_no;
    epoch_revision=work.faults->active_revision; epoch_internal=work.faults->internal;
    epoch_first=work.protection->first; epoch_mode=work.protection->mode;
    memcpy(epoch_alarm,work.protection->alarm_latch,sizeof epoch_alarm);
    memset(&cache,0,sizeof cache); build_index=0; phase=(buffer[1]&128u)?3:0;
}
static bool unchanged(const settings_t *cfg,const scan_out_t *scan) {
    mb_status_t status;
    if(cfg!=work.settings || scan!=work.scan || app_protection()!=work.protection ||
       app_faults()!=work.faults || cfg->sequence!=epoch_settings || scan->scan_no!=epoch_scan ||
       work.faults->active_revision!=epoch_revision || work.faults->internal!=epoch_internal ||
       work.protection->mode!=epoch_mode ||
       memcmp(&work.protection->first,&epoch_first,sizeof epoch_first)!=0 ||
       memcmp(work.protection->alarm_latch,epoch_alarm,sizeof epoch_alarm)!=0) return false;
    mb_io_status(&status);
    return memcmp(status.trip_latched,work.status.trip_latched,MB_BITMAP_BYTES)==0;
}
static uint8_t popcount(uint8_t v) {
    v=(uint8_t)(v-((v>>1)&0x55u)); v=(uint8_t)((v&0x33u)+((v>>2)&0x33u));
    return (uint8_t)((v+(v>>4))&15u);
}
static void build_step(void) {
    uint8_t i,j;
    switch(phase) {
    case 0: /* At most four channels, never a whole-board classification loop. */
        for(i=0;i<4 && build_index<work.settings->channel_count;i++,build_index++) {
            cache.state[build_index]=mb_channel_state(&work,build_index);
            if(cache.state[build_index]>=2) ++cache.alarms;
        }
        if(build_index==work.settings->channel_count) { build_index=0; phase=1; }
        break;
    case 1: /* Four code rows (48 bytes) per call, constant-time bit counting. */
        for(i=0;i<4 && build_index<FAULT_CODES;i++,build_index++) {
            bool active=false;
            for(j=0;j<FAULT_BYTES;j++) {
                uint8_t v=work.faults->active[build_index][j];
                if(v) active=true;
                if(build_index>0 && build_index<=FC_B15_ADC_RESET &&
                   build_index!=FC_G11_RESET_WDT && build_index!=FC_G12_RESET_BOD) cache.alarms+=popcount(v);
            }
            if(build_index==FC_G04_INTERNAL && epoch_internal) {
                if(!active) ++cache.alarms;
                active=true;
            }
            if(active) cache.faults[build_index/16u]|=(uint16_t)(1u<<(build_index%16u));
        }
        if(build_index==FAULT_CODES) { work.cache=&cache; build_index=0; phase=2; }
        break;
    case 2: /* Two registers; leave time for the real ISR/driver, not just fakes. */
        for(i=0;i<2 && build_index<buffer[2]/2u;i++) {
            uint16_t v=mb_register(&work,(uint16_t)(start_register+build_index));
            buffer[3+2*build_index]=(uint8_t)(v>>8); buffer[4+2*build_index]=(uint8_t)v;
            ++build_index;
        }
        if(build_index==buffer[2]/2u) phase=3;
        break;
    default: /* Sixteen CRC bytes; then borrowed binary TX, never wait for UART. */
        for(i=0;i<16 && tx_pos<tx_length-2;i++,tx_pos++) tx_crc=crc_byte(tx_crc,buffer[tx_pos]);
        if(tx_pos==tx_length-2) {
            buffer[tx_length-2]=(uint8_t)tx_crc; buffer[tx_length-1]=(uint8_t)(tx_crc>>8);
            if(mb_io_tx_start(buffer,tx_length)) { tx_owned=true; tx_length=0; }
        }
        break;
    }
}
void mb_task(uint16_t budget_us) {
    const settings_t *cfg; const scan_out_t *scan; mb_rx_t entry;
    uint32_t now,t15,t35; uint8_t i; bool busy;
    if(budget_us<1000) return;
    cfg=app_settings(); scan=scan_last();
    if(!cfg || !scan) return;
    busy=mb_io_tx_busy();
    if(cfg->address<1 || cfg->address>247 || cfg->baud>1) {
        configured=false; receiving=false; resync=true; tx_length=0; return;
    }
    if(!configured || cfg->address!=address || cfg->baud!=baud_code) {
        if(busy) return; /* borrowed TX storage/configuration must remain stable */
        address=cfg->address; baud_code=cfg->baud; mb_io_configure(baud_code);
        configured=true; receiving=false; resync=true; length=tx_length=0; last_rx=mb_io_now_us();
    }
    /* 8N2 = 11 bits: t1.5 = 859.375/1718.75us. On the 50us grid,
     * 850/1700 are the last accepted deltas; 900/1750 discard the frame.
     * t3.5 uses the explicit conservative 2/4ms policy of spec 07 section 1. */
    t15=baud_code?850u:1700u; t35=baud_code?2000u:4000u;
    history(cfg,scan);
    if(tx_owned && !busy) { tx_owned=false; resync=false; }
    /* While TX borrows storage, drain echo/noise without touching it. */
    if(tx_owned || busy) {
        for(i=0;i<RX_STEP;i++) { if(!mb_io_rx(&entry)) break; last_rx=entry.at_us; }
        resync=true; return;
    }
    if(tx_length) {
        if(mb_io_rx(&entry)) { tx_length=0; resync=true; last_rx=entry.at_us; return; }
        if(!unchanged(cfg,scan)) { tx_length=0; resync=true; return; }
        build_step();
        return;
    }
    for(i=0;i<RX_STEP;i++) {
        uint32_t gap;
        if(!mb_io_rx(&entry)) break;
        gap=entry.at_us-last_rx;
        if(resync) { if(gap>=t35) resync=false; }
        if(receiving && gap>=t35) {
            /* Master already started another frame: drop the old request
             * without answering into a busy bus. */
            receiving=false;
        }
        if(!resync) {
            if(!receiving) { receiving=true; length=0; rx_crc=0xFFFF; bad=false; }
            else if(gap>t15) bad=true;
            if(entry.flags) bad=true;
            if(length<sizeof buffer) { buffer[length++]=entry.byte; rx_crc=crc_byte(rx_crc,entry.byte); }
            else bad=true;
        }
        last_rx=entry.at_us;
    }
    now=mb_io_now_us();
    /* If the drain cap was hit, more bytes may already be queued: do not infer
     * silence from wall time until a later empty pop proves the queue drained. */
    if(i==RX_STEP) return;
    if(resync && now-last_rx>=t35) resync=false;
    if(receiving && now-last_rx>=t35) {
        respond(cfg,scan); receiving=false;
        /* CRC/send are separate steps, so this call captures only this loop's
         * immutable snapshot. TX turnaround already exceeds t3.5. */
    }
}
