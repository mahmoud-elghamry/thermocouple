#include "services/scan.h"
#include "app/acquisition_budget.h"
#include "app/cj_schedule.h"
#include "services/tc_math.h"
#include "drivers/ad7124.h"
#include "drivers/tmp126.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include "mcal/wdt.h"
#include "board/board_cfg.h"
#include <string.h>
typedef enum { INIT_ADC, INIT_CJ, WAIT_CJ, REF_PRE, REF_HIGH, REF_LOW,
               BEGIN_SCAN, BEGIN_BANK, START_SLOT, POLL_SLOT, END_SCAN, RECOVER } phase_t;
static phase_t phase;
static scan_out_t work,published;
static scan_diag_t diag;
static const settings_t *cfg;
static const calibration_t *cal;
static fault_registry_t *registry;
static uint32_t start,progress,wait_start,pending,last_ref;
static uint8_t initialized,slot,done,cj_index,end_index;
static bool prior[MAX_BANKS],good[MAX_BANKS],verify_done[MAX_BANKS],reinit,transport[MAX_BANKS];
static int32_t cj_mC[10];
static bool cj_valid[10];
static uint16_t cm_bad[MAX_BANKS];
static void raise(fault_code_t f,uint8_t u) { if(registry && f!=FC_NONE) (void)fault_raise(registry,f,u); }
static void bank_fault(uint8_t b,fault_code_t f) {
    if(f==FC_NONE) f=FC_B05_ADC_STALLED;
    good[b]=false; if(f!=FC_B06_REF) diag.cal_safe[b]=false; raise(f,b);
}
emf_nV_t scan_emf(uint32_t code,uint8_t gain) {
    int64_t d=(int32_t)code-0x800000L;
    /* Symmetric nearest rounding; avoids implementation-dependent negative shifts. */
    int64_t n=d*2500000000LL,div=(int64_t)gain*8388608L;
    if(gain==1) n=n>=0?(n+(1L<<22))>>23:-(((-n)+(1L<<22))>>23);
    else if(gain==32) n=n>=0?(n+(1L<<27))>>28:-(((-n)+(1L<<27))>>28);
    else n=n>=0?(n+div/2)/div:-((-n+div/2)/div);
    if(n>INT32_MAX) return INT32_MAX;
    if(n<INT32_MIN) return INT32_MIN;
    return (emf_nV_t)n;
}
fault_code_t scan_limit(uint8_t s,uint32_t code,uint32_t partner,int32_t ref,
                       int32_t baseline,uint32_t tc) {
    int32_t d=(int32_t)code-0x800000L,v=scan_emf(code,s==11 || s==12?1:32);
    int32_t other; int64_t diff;
    switch(s) {
    case 8: { /* OPEN-Q9: +/-1.6% from production ratio */
        int64_t nominal=6990507LL*(1000000LL+ref)/1000000LL;
        if(ref==CAL_MISSING || ref < -10000 || ref>10000 ||
           (int64_t)d*1000<nominal*984 || (int64_t)d*1000>nominal*1016) return FC_B06_REF;
        break;
    }
    case 9: if(v < -50000 || v>50000) return FC_B08_ZERO; break;
    case 10: if(v<15000000 || v>25000000) return FC_B09_GAIN; break;
    case 11:
        other=scan_emf(partner,32); diff=(int64_t)other-v;
        if(v<=0 || (int64_t)diff*1000 < -(int64_t)v*5 || (int64_t)diff*1000>(int64_t)v*5) return FC_B09_GAIN;
        break;
    case 12: /* AVDD=6*V; compare without overflowing int32. */
        if((int64_t)v*6<3150000000LL || (int64_t)v*6>3450000000LL) return FC_B07_AVDD;
        break;
    case 13: if(d*20LL<8388608LL || d*20LL>19LL*8388608LL) return FC_C03_COMMON_MODE; break;
    case 14:
        if(d>=7549748L) return FC_C01_OPEN;
        if(baseline==CAL_MISSING) return FC_G10_CALIBRATION; /* OPEN-Q10: lock, never invent baseline */
        diff=v-scan_emf(tc,32);
        if((int64_t)diff>2LL*baseline) return FC_C01_OPEN;
        if(2LL*diff<baseline) return FC_C06_SHORTED;
        break;
    default: if(d<=-8220836L || d>=8220836L) return FC_C02_RANGE; break;
    }
    return FC_NONE; /* All diagnostic windows provisional: 03 section 4. */
}
void scan_restart(void) {
    phase=INIT_ADC; initialized=0; cj_index=end_index=0; reinit=false; diag.initialized=false;
    diag.ref_test_ok=false; wait_start=tick_ms(); ad_reset_state(); cj_reset();
    memset(prior,0,sizeof prior); gpio_write(board()->reftest,false);
}
void scan_init(const settings_t *s,const calibration_t *c,fault_registry_t *r) {
    cfg=s; cal=c; registry=r; memset(&published,0,sizeof published); memset(&work,0,sizeof work);
    memset(cm_bad,0,sizeof cm_bad);
    memset(&diag,0,sizeof diag); pending=0; progress=tick_ms(); last_ref=tick_ms(); scan_restart();
}
static void publish(void) {
    uint8_t b,c; bool all=true,all_transport=true,all_fault=true;
    work.scan_validated=true;
    for(b=0;b<board()->banks;b++) {
        work.bank[b]=good[b]?BANK_VALIDATED:BANK_FAULT; all&=good[b]; all_transport&=transport[b]; all_fault&=!good[b];
        prior[b]=good[b];
    }
    if(all_transport || (gpio_read(board()->refok) && all_fault)) { raise(FC_G14_ISLAND_LOST,0); reinit=true; }
    if(gpio_read(board()->refok)) { raise(FC_G08_ENGREF_LOST,0); all=false; }
    diag.duration_ms=(uint16_t)(tick_ms()-start);
    if(tick_ms()-start>1000) { raise(FC_G05_SCAN_DEADLINE,0); all=false; }
    if(!fuses_ok()) { raise(FC_G15_FUSES,0); all=false; }
    if(registry && fault_active(registry,FC_G15_FUSES)) all=false;
    work.scan_validated=all && diag.ref_test_ok && !reinit;
    for(b=0;b<board()->banks;b++) diag.cal_safe[b]&=diag.registers_ok[b] && !reinit;
    work.completed_ms=tick_ms();
    /* Bad bank diagnostics revoke current validity; channel failures do not invalidate its bank. */
    for(c=0;c<board()->channels;c++) if(!good[board()->channel[c].bank]) work.meas[c].flags&=0xFE;
    published=work;
    if(work.scan_validated && registry) {
        fault_clear(registry,FC_G05_SCAN_DEADLINE,0); fault_clear(registry,FC_G08_ENGREF_LOST,0);
        fault_clear(registry,FC_G14_ISLAND_LOST,0);
    }
    phase=reinit?RECOVER:BEGIN_SCAN; wait_start=tick_ms(); progress=tick_ms();
}
static void channel_fault(uint8_t ch,fault_code_t f) {
    uint8_t flag=0;
    switch(f) {
    case FC_C01_OPEN:flag=MEAS_OPEN;break; case FC_C02_RANGE:flag=MEAS_RANGE;break;
    case FC_C03_COMMON_MODE:flag=MEAS_CM_FAIL;break; case FC_C06_SHORTED:flag=MEAS_SHORTED;break;
    case FC_C07_OVUV:flag=MEAS_OVUV;break; case FC_C08_COLD:flag=MEAS_COLD;break;
    default:break;
    }
    work.meas[ch].flags=(uint8_t)((work.meas[ch].flags&~MEAS_VALID)|flag);
    if(f!=FC_C03_COMMON_MODE) raise(f,ch); /* C03 registry unit is the physical input pin. */
}
static void result(uint8_t b,uint32_t code) {
    uint8_t ch=(uint8_t)(8*b+slot),target=(uint8_t)(8*b+work.scan_no%8);
    fault_code_t f=ad_fault(b),limit; int32_t base=CAL_MISSING,ref=CAL_MISSING;
    diag.raw[b][slot]=code;
    if(slot==8 && f!=FC_NONE) diag.cal_safe[b]=false;
    if(cal) { ref=cal->ref_ppm[b];
        if(cfg && cal->tag[target]==(uint8_t)((cfg->ch[target].type_epoch<<2)|cfg->ch[target].type)) base=cal->baseline_nV[target];
    }
    if(f>=FC_B01_ADC_ID && f<=FC_B15_ADC_RESET) bank_fault(b,f);
    else if(f!=FC_NONE) channel_fault(slot<8?ch:slot==13?(uint8_t)(8*b+(work.scan_no%16)/2):target,f);
    limit=scan_limit(slot,code,diag.raw[b][10],ref,base,diag.raw[b][work.scan_no%8]);
    if(limit>=FC_B01_ADC_ID && limit<=FC_B15_ADC_RESET) bank_fault(b,limit);
    /* OFF has no learned baseline/tag (05 §6). Its burnout result cannot
     * lock a partially fitted board; REF calibration remains mandatory. */
    if(slot==14 && cfg && cfg->ch[target].type==CH_TYPE_OFF) limit=FC_NONE;
    if(limit==FC_G10_CALIBRATION) raise(limit,0);
    if(slot<8) {
        result_t *m=&work.meas[ch];
        m->scan_no=work.scan_no; m->emf_nV=scan_emf(code,32); m->temp_dC=TEMP_DC_INVALID;
        /* Advisory CM/burn flags persist until their next scheduled check. */
        m->flags&=(MEAS_CM_FAIL|MEAS_OPEN|MEAS_SHORTED);
        if(limit!=FC_NONE) channel_fault(ch,limit);
        else if(f!=FC_NONE) channel_fault(ch,f);
        else if(good[b] && cj_valid[2*b] && cj_valid[2*b+1]) {
            uint16_t w=board()->channel[ch].cj_weight_q8;
            int32_t cj=cj_mC[2*b]+(int32_t)(((cj_mC[2*b+1]-cj_mC[2*b])*(int32_t)w)/256);
            ch_type_t type=cfg?cfg->ch[ch].type:CH_TYPE_K;
            uint8_t flags=tc_convert(type,m->emf_nV,(temp_dC_t)(cj/100),&m->temp_dC);
            m->flags|=(uint8_t)(flags&~MEAS_VALID);
            if(prior[b] && (flags&MEAS_VALID) && !(m->flags&~MEAS_VALID)) m->flags|=MEAS_VALID;
            if(flags&MEAS_COLD) raise(FC_C08_COLD,ch);
            if(flags&MEAS_RANGE) raise(FC_C02_RANGE,ch);
            if(registry && !(flags&MEAS_RANGE)) fault_clear(registry,FC_C02_RANGE,ch);
            if(registry && !(flags&MEAS_COLD)) fault_clear(registry,FC_C08_COLD,ch);
            if(registry) fault_clear(registry,FC_C07_OVUV,ch);
        }
        pending|=1UL<<ch;
    } else if(slot==13) {
        uint8_t input=(uint8_t)(work.scan_no%16);
        uint16_t bit=(uint16_t)(1u<<input);
        target=(uint8_t)(8*b+(work.scan_no%16)/2);
        if(limit!=FC_NONE || f==FC_C03_COMMON_MODE) { cm_bad[b]|=bit; channel_fault(target,FC_C03_COMMON_MODE); raise(FC_C03_COMMON_MODE,target); }
        else { cm_bad[b]&=(uint16_t)~bit; }
        /* One registry unit per owning channel, retaining both physical pin
         * bits until each clears. Raw pin identity remains in scan_no % 16. */
        if(registry && !(cm_bad[b]&(uint16_t)(3u<<(2*(input/2))))) fault_clear(registry,FC_C03_COMMON_MODE,target);
        if(!(cm_bad[b]&(uint16_t)(3u<<(2*(input/2))))) work.meas[target].flags&=0xF7;
    } else if(slot==14) {
        diag.burnout_nV[target]=scan_emf(code,32)-scan_emf(diag.raw[b][work.scan_no%8],32);
        if(limit==FC_C01_OPEN || limit==FC_C06_SHORTED) channel_fault(target,limit);
        else if(limit==FC_NONE && f==FC_NONE) { work.meas[target].flags&=0xED;
            if(registry) { fault_clear(registry,FC_C01_OPEN,target); fault_clear(registry,FC_C06_SHORTED,target); }
        }
    }
}
/* One current-scan CJ frame per pass. STATUS/RDY is still polled for every
 * bank; held DATA is processed after all six CJ records have been checked. */
static void cj_task(void) {
    uint8_t b; res_t r;
    if(cj_index>=board()->cj_count) return;
    r=cj_read_step(cj_index,&cj_mC[cj_index]); progress=tick_ms();
    if(r==RES_BUSY) return;
    diag.cj_status[cj_index]=r; cj_valid[cj_index]=r==RES_OK;
    if(++cj_index!=board()->cj_count) return;
    for(b=0;b<board()->banks;b++) {
        int32_t diff=cj_mC[2*b]-cj_mC[2*b+1];
        work.cj_dC[b][0]=(temp_dC_t)(cj_mC[2*b]/100); work.cj_dC[b][1]=(temp_dC_t)(cj_mC[2*b+1]/100);
        if(!cj_valid[2*b] && !cj_valid[2*b+1]) bank_fault(b,FC_B10_CJ_BOTH);
        else if(!cj_valid[2*b] || !cj_valid[2*b+1]) bank_fault(b,FC_B12_CJ_ONE);
        else if(diff < -3000 || diff>3000) bank_fault(b,FC_B11_CJ_DIFF);
    }
}
void scan_task(void) {
    uint8_t b; res_t r; uint32_t code=0; bool handled=false;
    switch(phase) {
    case INIT_ADC:
        for(b=0;b<board()->banks;b++) {
            uint8_t bank=end_index++;
            if(end_index==board()->banks) end_index=0;
            if(initialized&(1u<<bank)) continue;
            r=ad_init(bank);
            if(r==RES_OK) initialized|=(uint8_t)(1u<<bank);
            else if(r!=RES_BUSY) { raise(ad_fault(bank),bank); phase=RECOVER; wait_start=tick_ms(); }
            break;
        }
        progress=tick_ms();
        if(initialized==(1u<<board()->banks)-1u) { phase=INIT_CJ; cj_index=0; }
        break;
    case INIT_CJ:
        r=cj_init(cj_index); progress=tick_ms();
        if(r!=RES_OK) { raise(FC_B10_CJ_BOTH,(uint8_t)(cj_index/2)); phase=RECOVER; wait_start=tick_ms(); }
        else if(++cj_index==board()->cj_count) { cj_index=0; phase=WAIT_CJ; wait_start=tick_ms(); }
        break;
    case WAIT_CJ: if(tick_ms()-wait_start>=8) { diag.initialized=true; phase=REF_PRE; progress=tick_ms(); } break;
    case REF_PRE:
        if(gpio_read(board()->refok)) { raise(FC_G08_ENGREF_LOST,0); diag.ref_test_ok=false; phase=BEGIN_SCAN; }
        else { gpio_write(board()->reftest,true); phase=REF_HIGH; wait_start=tick_ms(); }
        progress=tick_ms(); break;
    case REF_HIGH:
        if(tick_ms()-wait_start>=5) { /* OPEN-H7: RC-estimated waits, 10 min interval */
            diag.ref_test_ok=gpio_read(board()->refok);
            if(!diag.ref_test_ok) raise(FC_G09_ENGREF_TEST,0);
            gpio_write(board()->reftest,false); phase=REF_LOW; wait_start=tick_ms(); progress=tick_ms();
        } break;
    case REF_LOW:
        if(tick_ms()-wait_start>=20) {
            if(gpio_read(board()->refok)) { raise(FC_G08_ENGREF_LOST,0); diag.ref_test_ok=false; }
            if(diag.ref_test_ok && registry) fault_clear(registry,FC_G09_ENGREF_TEST,0);
            last_ref=tick_ms(); diag.initialized=true; phase=BEGIN_SCAN; progress=tick_ms();
        } break;
    case BEGIN_SCAN:
        if(tick_ms()-last_ref>=600000UL) { phase=REF_PRE; break; }
        start=tick_ms(); ++work.scan_no; work.scan_validated=false; work.settings_seq=cfg?cfg->sequence:0;
        for(b=0;b<board()->banks;b++) {
            good[b]=true; transport[b]=false; verify_done[b]=false; diag.cal_safe[b]=true; diag.registers_ok[b]=false;
        }
        cj_index=end_index=0; phase=BEGIN_BANK; break;
    case BEGIN_BANK:
        b=end_index++; ad_scan_begin(b,work.scan_no);
        if(ad_fault(b)!=FC_NONE) { bank_fault(b,ad_fault(b)); reinit=true; }
        if(end_index==board()->banks) { end_index=0; slot=0; done=0; phase=reinit?END_SCAN:START_SLOT; }
        break;
    case START_SLOT:
        done=0;
        for(b=0;b<board()->banks;b++) {
            r=ad_start_slot(b,slot);
            if(r!=RES_OK) { bank_fault(b,ad_fault(b)); transport[b]=r==RES_ERR_CRC || r==RES_ERR_ID; reinit=true; }
        }
        progress=tick_ms(); end_index=0; phase=reinit?END_SCAN:POLL_SLOT; break;
    case POLL_SLOT:
        cj_task();
        for(b=0;b<board()->banks;b++) if(!(done&(1u<<b))) {
            r=ad_ready(b); /* P3 for every bank, even when another DATA completes. */
            if(r==RES_OK && !handled && cj_index==board()->cj_count) { r=ad_poll(b,&code); handled=true;
                if(r==RES_OK) { result(b,code); done|=(uint8_t)(1u<<b); }
            }
            if(r!=RES_OK && r!=RES_BUSY) { bank_fault(b,ad_fault(b)); transport[b]=r==RES_ERR_CRC || r==RES_ERR_ID; reinit=true; done|=(uint8_t)(1u<<b); }
            progress=tick_ms();
        }
        if(!handled && !reinit) {
            b=end_index++; if(end_index==board()->banks) end_index=0;
            if(!verify_done[b]) { r=ad_verify(b);
                if(r==RES_OK) verify_done[b]=true;
                else if(r!=RES_BUSY) { bank_fault(b,ad_fault(b)); reinit=true; }
            }
        }
        if(reinit) { if(done==(1u<<board()->banks)-1u) { end_index=0; phase=END_SCAN; } break; }
        if(done==(1u<<board()->banks)-1u) { end_index=0; if(++slot==15) phase=END_SCAN; else phase=START_SLOT; }
        break;
    case END_SCAN:
        if(!reinit) for(b=0;b<board()->banks;b++) {
            r=ad_verify_mutable_part(b,end_index); diag.registers_ok[b]=r==RES_OK && verify_done[b];
            if(!diag.registers_ok[b]) {
                bank_fault(b,ad_fault(b)); transport[b]=r==RES_ERR_CRC || r==RES_ERR_ID; reinit=true;
            }
            if(end_index==18 && good[b] && registry) { uint8_t f; for(f=FC_B01_ADC_ID;f<=FC_B15_ADC_RESET;f++) fault_clear(registry,(fault_code_t)f,b); }
        }
        if(!reinit && ++end_index<19) { progress=tick_ms(); break; }
        publish(); break;
    case RECOVER:
        if(tick_ms()-wait_start>=10) { scan_restart(); progress=tick_ms(); }
        break;
    default: raise(FC_G04_INTERNAL,0); scan_restart(); break;
    }
}
const scan_out_t *scan_last(void) { return &published; }
const scan_out_t *scan_current(void) { return &work; }
const scan_diag_t *scan_diagnostics(void) { return &diag; }
uint32_t scan_progress_ms(void) { return progress; }
uint32_t scan_take_results(void) { uint32_t v=pending; pending=0; return v; }
