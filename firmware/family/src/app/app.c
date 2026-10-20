#include "app/app.h"
#include "app/ack_input.h"
#include "app/ee_owner.h"
#include "app/outputs.h"
#include "app/outputs_hw.h"
#include "app/service.h"
#include "services/scan.h"
#include "services/events.h"
#include "drivers/relays.h"
#include "mcal/timer.h"
#include "mcal/wdt.h"
#include <string.h>
static settings_t *settings,mailbox;
static calibration_t *cal;
static fault_registry_t *faults;
static prot_state_t protection;
static prot_out_t output;
static outputs_t outputs;
static bool command_pending,service_mode,window_watch;
static bool trip_logged;
static uint32_t last_scan,window_at;
static uint16_t worst_loop;
static ack_reason_t last_ack;
static uint8_t seen_fault[FAULT_CODES][FAULT_BYTES],channel_cause[MAX_CHANNELS];
static void log_event(event_type_t type,fault_code_t code,uint8_t channel,uint8_t unit,
                      temp_dC_t value,temp_dC_t threshold) {
    event_t e;
    memset(&e,0,sizeof e); e.type=type; e.code=code; e.channel=channel; e.unit=unit;
    e.value_dC=value; e.threshold_dC=threshold; e.uptime_s=tick_ms()/1000u;
    if(type==EV_TRIP) trip_logged=true;
    if(!ee_owner_log(&e)) (void)fault_raise(faults,FC_G04_INTERNAL,0);
}
void app_init(settings_t *cfg,calibration_t *calibration,fault_registry_t *registry,
              bool valid,bool service) {
    prot_in_t in;
    settings=cfg; cal=calibration; faults=registry; service_mode=service;
    memset(&outputs,0,sizeof outputs); memset(&output,0,sizeof output);
    memset(seen_fault,0,sizeof seen_fault); memset(channel_cause,0,sizeof channel_cause);
    command_pending=window_watch=false; last_scan=0; worst_loop=0; last_ack=ACK_NONE;
    prot_init(&protection,valid,valid && cal_complete(cal,cfg),service);
    /* Publish fitted-channel identity before any fault notifications. */
    memset(&in,0,sizeof in); in.settings=settings; in.faults=faults;
    in.settings_valid=valid; in.calibration_valid=valid && cal_complete(cal,cfg);
    in.now_ms=tick_ms(); in.flow_ok=true; prot_step(&in,&protection,&output);
    ack_input_init();
    if(service) log_event(EV_SERVICE_ENTRY,FC_NONE,0,0,0,0);
}
res_t app_commit_settings(const settings_t *candidate) {
    if(!settings || !candidate || candidate->board_type!=settings->board_type ||
       candidate->channel_count!=settings->channel_count || set_validate(candidate)!=RES_OK) return RES_ERR_RANGE;
    if(command_pending || ee_owner_busy()) return RES_BUSY;
    mailbox=*candidate; command_pending=true; return RES_OK;
}
const settings_t *app_settings(void) { return settings; }
const prot_state_t *app_protection(void) { return &protection; }
const prot_out_t *app_output(void) { return &output; }
const fault_registry_t *app_faults(void) { return faults; }
ack_reason_t app_ack_reason(void) { return last_ack; }
uint16_t app_worst_loop_ms(void) { return worst_loop; }
void app_loop_time(uint16_t ms) { if(ms>worst_loop) worst_loop=ms; }
static void immediate_results(void) {
    uint32_t mask=scan_take_results(); uint8_t ch;
    const scan_out_t *scan=scan_current();
    if(!ee_owner_settings_valid()) return;
    for(ch=0;ch<settings->channel_count;ch++) if(mask&(1UL<<ch)) {
        const result_t *r=&scan->meas[ch]; const chan_cfg_t *c=&settings->ch[ch];
        cond_t condition=chan_cond(r,c,scan->scan_no);
        fault_code_t code=chan_cause(r,condition); act_t action=chan_action(condition,c->mode);
        prot_mode_t before=protection.mode;
        (void)prot_on_result(&protection,ch,r,settings,scan->scan_no,tick_ms()/1000u);
        if(action!=ACT_NONE && channel_cause[ch]!=(uint8_t)code) {
            log_event(action==ACT_TRIP?EV_TRIP:EV_ALARM,code,(uint8_t)(ch+1),0,r->temp_dC,
                      action==ACT_TRIP?c->trip_dC:c->alarm_dC);
        }
        channel_cause[ch]=action==ACT_NONE?0:(uint8_t)code;
        if(before==RUN && protection.mode!=RUN) ack_input_cancel();
    }
}
static void immediate_faults(void) {
    uint8_t code,byte,bit;
    for(code=1;code<FC_C10_OVER_TRIP;code++) for(byte=0;byte<FAULT_BYTES;byte++) {
        uint8_t active=faults->active[code][byte];
        uint8_t fresh=(uint8_t)(active&~seen_fault[code][byte]);
        seen_fault[code][byte]=active;
        for(bit=0;fresh && bit<8;bit++) if(fresh&(1u<<bit)) {
            uint8_t unit=(uint8_t)(8*byte+bit),ch=0,event_unit=0;
            ch_mode_t mode=CH_MODE_TRIP; bool fitted=true;
            prot_mode_t before=protection.mode;
            if(code>=FC_C01_OPEN && unit<settings->channel_count) {
                ch=(uint8_t)(unit+1); mode=settings->ch[unit].mode;
                fitted=settings->ch[unit].type!=CH_TYPE_OFF;
                if(code==FC_C03_COMMON_MODE) event_unit=(uint8_t)(scan_current()->scan_no%16u);
            } else if(code>=FC_B01_ADC_ID) event_unit=(uint8_t)(unit+1);
            (void)prot_on_fault(&protection,faults,(fault_code_t)code,unit,mode,ch,tick_ms()/1000u);
            if(fitted) {
                log_event(EV_FAULT,(fault_code_t)code,ch,event_unit,0,0);
                if(fault_action((fault_code_t)code,mode)==ACT_TRIP)
                    log_event(EV_TRIP,(fault_code_t)code,ch,event_unit,0,0);
            }
            if(before==RUN && protection.mode!=RUN) ack_input_cancel();
            fresh&=(uint8_t)~(1u<<bit);
        }
    }
}
uint8_t app_step(bool flow_ok) {
    prot_in_t in; output_decision_t d; uint8_t done,seen=0; res_t r;
    prot_mode_t before;
    memset(&in,0,sizeof in);
    trip_logged=false;
    if(command_pending) {
        r=ee_owner_settings(&mailbox);
        if(r!=RES_BUSY) { command_pending=false; if(r!=RES_OK) last_ack=ACK_R5_SETTINGS; }
    }
    done=ee_owner_take_done();
    in.commit_begin=ee_owner_take_begin(); in.commit_done=done!=0;
    in.protection_change=ee_owner_protection_change();
    if(in.commit_begin || in.commit_done) ack_input_cancel();
    if(done && in.protection_change && !service_mode) {
        /* Drop every result that could straddle a type/settings/calibration switch. */
        scan_init(settings,cal,faults); last_scan=0; memset(channel_cause,0,sizeof channel_cause);
    }
    if(service_mode) {
        /* Service owns the confirmed relay-test bypass and key queue. Settings
         * still use the same mailbox and durable owner as the later UI. */
        in.settings=settings; in.faults=faults; in.now_ms=tick_ms();
        in.settings_valid=ee_owner_settings_valid(); in.calibration_valid=cal_complete(cal,settings);
        in.flow_ok=flow_ok; in.writing=ee_owner_busy();
        /* No service measurement is protection evidence. Still execute the
         * state/complement checks, including during confirmed relay tests. */
        prot_step(&in,&protection,&output);
        if(protection.mode!=SERVICE) {
            service_mode=false; relays_safe(); return 3;
        }
        if(in.commit_begin && in.protection_change) relays_safe();
        if(done==1) {
            svc_settings_committed(ee_owner_settings_valid());
            log_event(in.protection_change?EV_SETTINGS_CHANGED:EV_NAME_CHANGED,FC_NONE,0,0,0,0);
        }
        if(scan_last()->scan_no!=last_scan && scan_last()->scan_validated)
            ee_owner_validated_scan(FC_NONE,tick_ms()/1000u);
        last_scan=scan_last()->scan_no;
        return 1;
    }
    if(done==2) log_event(EV_CALIBRATION,FC_NONE,0,0,0,0);
    if(ee_owner_fault()!=FC_NONE) (void)fault_raise(faults,ee_owner_fault(),0);
    if(ee_owner_fault()!=FC_G13_SAVE_FAIL_INFO) fault_clear(faults,FC_G13_SAVE_FAIL_INFO,0);
    if(ee_owner_fault()!=FC_G02_SAVE_FAIL_PROT) fault_clear(faults,FC_G02_SAVE_FAIL_PROT,0);
    immediate_results();
    /* Keep the last granted scan's freshness deadline even if B05 opens RUN
     * earlier. A stalled acquisition still records G05 after that window. */
    if(window_watch && tick_ms()-window_at>=900u) {
        (void)fault_raise(faults,FC_G05_SCAN_DEADLINE,0); window_watch=false;
    }
    immediate_faults();
    in.settings=settings; in.scan=scan_last(); in.faults=faults;
    in.now_ms=tick_ms(); in.uptime_s=in.now_ms/1000u;
    in.settings_valid=ee_owner_settings_valid(); in.calibration_valid=cal_complete(cal,settings);
    in.writing=ee_owner_busy(); in.flow_ok=flow_ok;
    in.scan_complete=in.scan->scan_no!=last_scan; last_scan=in.scan->scan_no;
    in.readback_off_ok=!relay_run_sense() && !relay_alarm_sense();
    ack_input_step(&in); before=protection.mode;
    prot_step(&in,&protection,&output);
    seen|=1;
    if(in.scan_complete && in.scan->scan_validated) window_watch=false;
    if(output.window_refresh) { window_watch=true; window_at=in.now_ms; }
    if(in.ack) last_ack=output.ack_reason;
    if(before==RUN && protection.mode!=RUN) ack_input_cancel();
    d=outputs_step(&outputs,&output,tick_ms(),!relay_run_sense(),!relay_alarm_sense());
    outputs_hw_apply(d.pwm_enable,d.alarm_energise,output.window_remaining_ms);
    seen|=2;
    if(d.run_fault!=FC_NONE) (void)fault_raise(faults,d.run_fault,0);
    else fault_clear(faults,FC_G06_RUN_FEEDBACK,0);
    if(d.alarm_fault!=FC_NONE) (void)fault_raise(faults,d.alarm_fault,0);
    else fault_clear(faults,FC_G07_ALARM_FEEDBACK,0);
    /* Feedback faults reach protection in this pass; PWM already stopped. */
    immediate_faults();
    if(protection.mode!=RUN) {
        output.run_permission=false; output.window_remaining_ms=0; output.alarm_active=true;
    }
    if(output.event_mask) {
        uint8_t event;
        for(event=EV_TRIP;event<=EV_PIN_RESET;event++) if(output.event_mask&(1u<<(event-1))) {
            const first_out_t *f=&protection.first;
            if(event==EV_TRIP && trip_logged) continue;
            log_event((event_type_t)event,event==EV_TRIP?f->code:FC_NONE,
                      event==EV_TRIP?f->channel:0,event==EV_TRIP?f->unit:0,
                      event==EV_TRIP?f->value_dC:0,event==EV_TRIP?f->threshold_dC:0);
        }
    }
    if(in.scan_complete && in.scan->scan_validated) {
        uint8_t reset=reset_cause();
        ee_owner_validated_scan((reset&8u)?FC_G11_RESET_WDT:(reset&4u)?FC_G12_RESET_BOD:FC_NONE,in.uptime_s);
    }
    return seen;
}
