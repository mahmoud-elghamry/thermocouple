/* Tests specified before implementation. Deliberately independent bitwise CRC
 * and expected wire tables, never the production map as the test oracle. */
#include "app/modbus.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Internal streaming-map entry point also defends against malformed indices. */
uint16_t mb_register(const mb_snapshot_t *s,uint16_t address);

static unsigned long checks;
#define CHECK(x) do { ++checks; if(!(x)) { printf("FAIL line %u: %s\n",(unsigned)__LINE__,#x); exit(1); } } while(0)
static settings_t cfg;
static scan_out_t scan;
static prot_state_t prot;
static fault_registry_t faults;
static uint16_t ages[MAX_CHANNELS];
static mb_status_t status;
static uint32_t now;
static unsigned pops, configurations, transmissions;
static uint8_t baud, sent[256];
static uint16_t sent_n;
static const uint8_t *borrowed;
static bool busy;
static mb_rx_t queue[2048];
static unsigned head, tail;
static uint16_t crc(const uint8_t *p,uint16_t n) {
    uint16_t c=0xFFFF; uint8_t k;
    while(n--) { c^=*p++; for(k=0;k<8;k++) c=(uint16_t)((c>>1)^((c&1)?0xA001:0)); }
    return c;
}
static uint16_t finish(uint8_t *p,uint16_t n) {
    uint16_t c=crc(p,n); p[n]=(uint8_t)c; p[n+1]=(uint8_t)(c>>8); return (uint16_t)(n+2);
}
static void request(uint8_t *r,uint8_t fn,uint16_t addr,uint16_t count) {
    r[0]=17; r[1]=fn; r[2]=(uint8_t)(addr>>8); r[3]=(uint8_t)addr;
    r[4]=(uint8_t)(count>>8); r[5]=(uint8_t)count; (void)finish(r,6);
}
const settings_t *app_settings(void) { return &cfg; }
const prot_state_t *app_protection(void) { return &prot; }
const fault_registry_t *app_faults(void) { return &faults; }
ack_reason_t app_ack_reason(void) { return ACK_R4_CHANNEL; }
const scan_out_t *scan_last(void) { return &scan; }
void mb_io_configure(uint8_t b) { baud=b; ++configurations; }
uint32_t mb_io_now_us(void) { return now; }
bool mb_io_rx(mb_rx_t *r) { ++pops; if(tail==head) return false; *r=queue[tail++]; return true; }
bool mb_io_tx_start(const uint8_t *p,uint16_t n) {
    if(busy) return false;
    CHECK(n<=sizeof sent); borrowed=p; memcpy(sent,p,n); sent_n=n; ++transmissions; busy=true; return true;
}
bool mb_io_tx_busy(void) { return busy; }
void mb_io_status(mb_status_t *s) { *s=status; }
static mb_snapshot_t snapshot(void) {
    mb_snapshot_t s;
    memset(&s,0,sizeof s); s.settings=&cfg; s.scan=&scan; s.protection=&prot; s.faults=&faults;
    s.age=ages; s.status=status; s.have_validated=true; s.last_validated_ms=100;
    s.ack_reason=ACK_R4_CHANNEL; return s;
}
static void fixture(uint8_t channels) {
    uint8_t ch;
    memset(&cfg,0,sizeof cfg); memset(&scan,0,sizeof scan); memset(&prot,0,sizeof prot);
    memset(&faults,0,sizeof faults); memset(&status,0,sizeof status);
    cfg.board_type=channels; cfg.channel_count=channels; cfg.address=17;
    cfg.sequence=9; scan.settings_seq=9; scan.scan_no=0x12345678UL; scan.scan_validated=true;
    scan.completed_ms=100; status.now_ms=321; status.uptime_s=0xABCDEF01UL;
    status.power_cycles=0x12345678UL; status.version=0x0203; status.patch=4; status.schema=1;
    status.run_driven=true; status.alarm_driven=false; prot.mode=TRIPPED;
    prot.first.valid=true; prot.first.code=FC_C10_OVER_TRIP; prot.first.channel=3;
    prot.first.value_dC=-12; prot.first.threshold_dC=6000;
    for(ch=0;ch<channels;ch++) {
        cfg.ch[ch].type=CH_TYPE_K; cfg.ch[ch].mode=CH_MODE_TRIP;
        cfg.ch[ch].alarm_dC=(int16_t)(4000+ch); cfg.ch[ch].trip_dC=(int16_t)(6000+ch);
        cfg.ch[ch].band_C=(uint8_t)(2+ch); cfg.ch[ch].probe_limit_dC=13000;
        memcpy(cfg.ch[ch].name,"ABCxyz",6); scan.meas[ch].flags=MEAS_VALID;
        scan.meas[ch].scan_no=scan.scan_no; scan.meas[ch].temp_dC=(int16_t)(-100+ch); ages[ch]=ch;
    }
    cfg.ch[0].type=CH_TYPE_OFF;
    scan.meas[1].temp_dC=5000; prot.alarm_latch[1]=1;
    scan.meas[2].temp_dC=7000; prot.alarm_latch[2]=1; status.trip_latched[0]=4;
    scan.meas[3].flags=MEAS_OPEN|MEAS_RANGE|MEAS_CM_FAIL;
    cfg.ch[4].type=CH_TYPE_J; cfg.ch[4].mode=CH_MODE_ALARM_ONLY;
    faults.active[FC_G08_ENGREF_LOST][0]=1;
    faults.active[FC_B15_ADC_RESET][0]=2;
    faults.active[FC_C01_OPEN][0]=8;
    now=0; head=tail=0; pops=configurations=transmissions=0; busy=false; sent_n=0;
}
static uint16_t expected(uint16_t a) {
    uint16_t globals[64]={1,24,24,0x0203,4,1,3,1,0,5,50,3,0xFFF4,6000,0x1234,0x5678,
        221,0x5678,0xABCD,0xEF01,0x0100,0,0x0208,0,0,0,0,0,4,0,0,0,0,0,0,0,
        14,0,0,0,0,0,0,0,8,0,0,0,0,0,0,0,4};
    uint8_t ch,off;
    globals[1]=cfg.board_type; globals[2]=cfg.channel_count;
    if(a<64) return globals[a];
    if(a>=600) { off=(uint8_t)((a-600)%3); return (uint16_t)((uint16_t)(uint8_t)"ABCxyz"[2*off]<<8)|(uint8_t)"ABCxyz"[2*off+1]; }
    ch=(uint8_t)((a-100)/10); off=(uint8_t)((a-100)%10);
    switch(off) {
    case 0: return ch==0 || ch==3?0x8000:(uint16_t)scan.meas[ch].temp_dC;
    case 1: return ch==0?0:(ch==1?2:(ch==2?3:(ch==3?4:1)));
    case 2: return ch==0?0:(ch==1?129:(ch==2?193:(ch==3?14:1)));
    case 3: return (uint16_t)cfg.ch[ch].type;
    case 4: return (uint16_t)cfg.ch[ch].mode;
    case 5: return (uint16_t)(4000+ch);
    case 6: return (uint16_t)(6000+ch);
    case 7: return (uint16_t)(2+ch);
    case 8: return ch;
    default: return 0;
    }
}
static void maps(void) {
    uint8_t boards[]={24},r[8],out[256],fn,b;
    uint16_t a,n,value; mb_snapshot_t s;
    for(b=0;b<sizeof boards;b++) { fixture(boards[b]); s=snapshot();
        for(fn=3;fn<=4;fn++) for(a=0;a<729;a++) {
            bool mapped=a<64 || (a>=100 && a<100+10*boards[b]) || (a>=600 && a<600+3*boards[b]);
            request(r,fn,a,1); memset(out,0xA5,sizeof out); n=mb_build(&s,r,8,out,sizeof out);
            CHECK(n==(mapped?7:5)); CHECK(crc(out,n)==0); CHECK(out[0]==17);
            if(mapped) { CHECK(out[1]==fn && out[2]==2); value=(uint16_t)((uint16_t)out[3]<<8)|out[4];
                if(value!=expected(a)) printf("board %u fn %u reg %u got %u expected %u\n",boards[b],fn,a,value,expected(a)); CHECK(value==expected(a)); }
            else CHECK(out[1]==(fn|0x80) && out[2]==2);
            CHECK(out[n]==0xA5);
        }
    }
}
static void frames(void) {
    uint8_t r[257],out[258]; uint16_t n,fn; mb_snapshot_t s;
    fixture(24); s=snapshot(); CHECK(mb_crc16((const uint8_t *)"123456789",9)==0x4B37);
    for(fn=0;fn<256;fn++) if(fn!=3 && fn!=4) {
        request(r,(uint8_t)fn,0,1); n=8;
        if(fn==16) { r[6]=2; r[7]=0; r[8]=1; n=finish(r,9); }
        CHECK(mb_build(&s,r,n,out,256)==5); CHECK(out[1]==(fn|128) && out[2]==1);
    }
    request(r,3,0,0); CHECK(mb_build(&s,r,8,out,256)==5 && out[2]==3);
    request(r,4,0,65); CHECK(mb_build(&s,r,8,out,256)==5 && out[2]==3);
    request(r,3,0,64); CHECK(mb_build(&s,r,8,out,256)==133); CHECK(out[2]==128 && crc(out,133)==0);
    CHECK(mb_build(&s,r,8,out,132)==0);
    memcpy(out,r,8); CHECK(mb_build(&s,out,8,out,256)==133 && crc(out,133)==0);
    r[7]^=1; CHECK(mb_build(&s,r,8,out,256)==0);
    request(r,3,0,1); r[0]=0; (void)finish(r,6); CHECK(mb_build(&s,r,8,out,256)==0);
    r[0]=18; (void)finish(r,6); CHECK(mb_build(&s,r,8,out,256)==0);
    request(r,3,0,1); for(n=0;n<8;n++) CHECK(mb_build(&s,r,n,out,256)==0);
    r[6]=0; CHECK(mb_build(&s,r,finish(r,7),out,256)==0);
    memset(r,0,sizeof r); CHECK(mb_build(&s,r,257,out,256)==0);
    request(r,3,63,2); CHECK(mb_build(&s,r,8,out,256)==5 && out[2]==2);
    request(r,3,1000,1); CHECK(mb_build(&s,r,8,out,256)==5 && out[2]==2);
    request(r,3,65535,64); CHECK(mb_build(&s,r,8,out,256)==5 && out[2]==2);
    memset(r,0,256); r[0]=17; r[1]=16; r[6]=247;
    CHECK(mb_build(&s,r,finish(r,254),out,256)==5 && out[2]==1);
    request(r,3,100,1); scan.scan_no=0; CHECK(mb_build(&s,r,8,out,256)==7 && out[3]==128 && out[4]==0);
    scan.scan_no=1; scan.meas[0].scan_no=1; cfg.ch[0].type=CH_TYPE_K; scan.settings_seq=0;
    CHECK(mb_build(&s,r,8,out,256)==7 && out[3]==128 && out[4]==0);
    CHECK(mb_build(NULL,r,8,out,256)==0); CHECK(mb_build(&s,NULL,8,out,256)==0);
    CHECK(mb_build(&s,r,8,NULL,256)==0);
}
static void enqueue(uint8_t byte,uint32_t at,uint8_t flags) {
    CHECK(head<2048); queue[head].byte=byte; queue[head].at_us=at; queue[head++].flags=flags; now=at;
}
static void task(void) { unsigned before=pops; mb_task(1000); CHECK(pops-before<=8); }
static void settle(void) { uint8_t i; for(i=0;i<64;i++) task(); }
static void ready(uint8_t b) {
    fixture(24); cfg.baud=b; mb_init(); task(); now=10000; task(); CHECK(configurations==1 && baud==b);
}
static uint32_t frame(uint32_t at,uint32_t spacing,uint8_t flags) {
    uint8_t r[8],i; request(r,3,0,1);
    for(i=0;i<8;i++) enqueue(r[i],at+(uint32_t)i*spacing,i==3?flags:0);
    task(); return now;
}
static void timing(void) {
    uint8_t b; uint32_t end,t15,t35;
    for(b=0;b<2;b++) {
        t15=b?850:1700; t35=b?2000:4000;
        ready(b); end=frame(12000,t15,0); now=end+t35-50; task(); CHECK(transmissions==0);
        now=end+t35; task(); settle(); CHECK(transmissions==1 && sent_n==7 && crc(sent,sent_n)==0);
        ready(b); end=frame(12000,t15+50,0); now=end+t35; task(); CHECK(transmissions==0);
        ready(b); end=frame(12000,b?600:1150,MB_RX_ERROR); now=end+t35; task(); CHECK(transmissions==0);
        ready(b); end=frame(12000,b?600:1150,0); now=end+t35;
        /* Another frame begins exactly at t3.5, while both are queued. */
        end=frame(now,b?600:1150,0); now=end+t35; task(); settle(); CHECK(transmissions==1 && crc(sent,sent_n)==0);
        ready(b); now=0xFFFFFF00UL; task(); end=frame(now+10000,b?600:1150,0);
        now=end+t35; task(); settle(); CHECK(transmissions==1);
    }
    ready(0); (void)frame(12000,1150,0); mb_task(999); CHECK(transmissions==0);
    /* Boot and framing resync discard bytes until a complete silent interval. */
    fixture(24); mb_init(); (void)frame(0,1150,0); now+=4000; task(); CHECK(transmissions==0);
    ready(0); end=frame(12000,1150,0); now=end+4000; task(); settle(); CHECK(transmissions==1);
    cfg.baud=1; cfg.address=23; busy=false; task(); CHECK(configurations==2 && baud==1);
}
static void flood(void) {
    unsigned i,j; uint32_t end; settings_t saved_cfg; prot_state_t saved_prot;
    ready(1);
    saved_cfg=cfg; saved_prot=prot;
    /* >10 minutes of continuous 19200-baud 8N2 garbage (687.5s), with
     * RX-complete timestamps quantised to the required 50us grid. */
    for(i=0;i<150000;i++) {
        head=tail=0;
        for(j=0;j<8;j++) {
            uint64_t bytes=(uint64_t)i*8u+j+1u;
            now=10000u+(uint32_t)((bytes*11000000u/19200u)/50u*50u);
            enqueue((uint8_t)(i+j),now,0);
        }
        task(); CHECK(transmissions==0);
    }
    CHECK(memcmp(&saved_cfg,&cfg,sizeof cfg)==0); CHECK(memcmp(&saved_prot,&prot,sizeof prot)==0);
    now+=2000; task(); head=tail=0;
    end=frame(now+2000,600,0); now=end+2000; task(); settle(); CHECK(transmissions==1);
}
static void bitmaps(void) {
    uint8_t r[8],out[256],code,ch; mb_snapshot_t s;
    fixture(24); s=snapshot(); memset(&faults,0,sizeof faults);
    for(code=1;code<FAULT_CODES;code++) {
        faults.active[code][11]=128; request(r,3,(uint16_t)(20+code/16),1);
        CHECK(mb_build(&s,r,8,out,256)==7);
        CHECK((((uint16_t)out[3]<<8)|out[4])==(uint16_t)(1u<<(code%16)));
        faults.active[code][11]=0;
    }
    memset(status.trip_latched,0,sizeof status.trip_latched);
    for(ch=1;ch<MAX_CHANNELS;ch++) {
        status.trip_latched[ch/8]|=(uint8_t)(1u<<(ch%8)); s.status=status;
        request(r,3,(uint16_t)(28+ch/16),1); CHECK(mb_build(&s,r,8,out,256)==7);
        CHECK(((((uint16_t)out[3]<<8)|out[4])&(1u<<(ch%16)))!=0);
    }
    faults.internal=true; request(r,3,20,1); CHECK(mb_build(&s,r,8,out,256)==7 && out[4]==16);
    s.have_validated=false; request(r,3,16,1); CHECK(mb_build(&s,r,8,out,256)==7 && out[3]==128 && out[4]==0);
    s.have_validated=true; s.status.now_ms=100000; request(r,3,16,1);
    CHECK(mb_build(&s,r,8,out,256)==7 && out[3]==255 && out[4]==255);
    prot.first.valid=false; request(r,3,10,4); CHECK(mb_build(&s,r,8,out,256)==13);
    for(ch=3;ch<11;ch++) CHECK(out[ch]==0);
}
static void runtime(void) {
    uint8_t r[257],i,which; uint32_t end;
    for(which=0;which<5;which++) {
        ready(1); end=frame(12000,600,0); now=end+2000; task();
        switch(which) {
        case 0: ++cfg.sequence; break;
        case 1: ++scan.scan_no; break;
        case 2: ++faults.active_revision; break;
        case 3: prot.alarm_latch[5]=1; break;
        default: status.trip_latched[0]^=1; break;
        }
        settle(); CHECK(transmissions==0);
        head=tail=0; end=frame(now+4000,600,0); now=end+2000; task(); settle(); CHECK(transmissions==1);
    }
    for(which=0;which<5;which++) {
        ready(1); request(r,3,0,1);
        if(which==0) r[7]^=1;
        if(which==1) { r[0]=0; (void)finish(r,6); }
        if(which==2) { r[0]=18; (void)finish(r,6); }
        if(which==3) { r[6]=0; (void)finish(r,7); }
        for(i=0;i<(which==3?9:(which==4?7:8));i++) enqueue(r[i],12000u+600u*i,0);
        task(); now+=2000; task(); settle(); CHECK(transmissions==0);
    }
    ready(1); request(r,3,0,64);
    for(i=0;i<8;i++) enqueue(r[i],12000u+600u*i,0);
    task(); now+=2000; task(); settle(); CHECK(sent_n==133 && crc(sent,sent_n)==0);
    /* Port retains the TX pointer until completion; hostile RX cannot overwrite it. */
    for(i=0;i<64;i++) { head=tail=0; enqueue(i,now+600,0); task(); }
    CHECK(transmissions==1 && memcmp(borrowed,sent,sent_n)==0); busy=false; head=tail=0; now+=2000; task();
    /* A new RX byte during a pending response cancels it. */
    ready(1); end=frame(12000,600,0); now=end+2000; task();
    head=tail=0; enqueue(0x55,now+500,0); task(); now+=2000; settle(); CHECK(transmissions==0);
    /* End-to-end age history: valid, invalid three scans, saturation. */
    ready(1); scan.meas[1].flags=0; scan.scan_no+=3; status.now_ms=100000;
    task(); request(r,3,118,1); head=tail=0;
    for(i=0;i<8;i++) enqueue(r[i],12000u+600u*i,0);
    task(); now+=2000; task(); settle(); CHECK(sent_n==7 && sent[3]==0 && sent[4]==3);
    busy=false; now+=2000; task(); scan.scan_no+=70000; task(); head=tail=0;
    for(i=0;i<8;i++) enqueue(r[i],now+600,0);
    task(); now+=2000; task(); settle(); CHECK(sent_n==7 && sent[3]==255 && sent[4]==255);
    /* Overlong frame shares the sole buffer, cannot overrun it; recover cleanly. */
    ready(1);
    { uint16_t j; for(j=0;j<264;j++) { enqueue((uint8_t)j,now+600,0); if(j%8==7) task(); } }
    now+=2000; task(); settle(); CHECK(transmissions==0);
    head=tail=0; end=frame(now+2000,600,0); now=end+2000; task(); settle(); CHECK(transmissions==1);
}
static void defensive_registers(void) {
    mb_snapshot_t s; uint32_t address;
    fixture(24); s=snapshot();
    for(address=64;address<=UINT16_MAX;address++) {
        if((address>=100 && address<340) || (address>=600 && address<672)) continue;
        CHECK(mb_register(&s,(uint16_t)address)==0);
    }
}
int main(void) { defensive_registers(); maps(); frames(); bitmaps(); timing(); runtime(); flood(); printf("Modbus: %lu checks PASS\n",checks); return 0; }
