#include "app/ui.h"
#include "services/scan.h"
#include "drivers/lcd.h"
#include "mcal/timer.h"
#include <string.h>
static ui_state_t state;
static char frame[80];
static uint8_t row;
static settings_t *candidate;
ui_screen_t ui_current_screen(void) { return state.screen; }
static void home(void) {
    state.screen=UI_HOME; state.session=false; state.pending=KEY_NONE;
    state.recovering=false; state.minimum=state.maximum=state.cj=TEMP_DC_INVALID;
    keys_repeat(false); row=0;
}
void ui_init(void) {
    memset(&state,0,sizeof state); memset(frame,' ',80); row=0;
    candidate=NULL;
    state.activity_ms=state.message_ms=tick_ms(); state.previous_mode=app_protection()->mode;
    memset(state.service_step,' ',4);
    state.minimum=state.maximum=state.cj=TEMP_DC_INVALID; keys_repeat(false);
}
bool ui_key(key_t key) {
    if(key==KEY_NONE || key==KEY_ACK || (unsigned)key>KEY_SET_LONG || state.pending!=KEY_NONE) return false;
    state.pending=key; return true;
}
void ui_ack_result(ack_reason_t reason) {
    state.ack_seen=reason;state.activity_ms=tick_ms();
    if(reason>=ACK_R1_RELEASE && reason<=ACK_R6_RELAY) {
        state.message=(ui_message_t)(UM_R1+reason-ACK_R1_RELEASE);state.message_ms=tick_ms();
    }
}
void ui_bind_candidate(settings_t *mailbox) { if(!state.transaction) candidate=mailbox; }
void ui_pin_recovery(void) { home();state.screen=UI_RECOVER;state.recovering=true; }
bool ui_take_pin_reset(void) { bool r=state.reset_pending;state.reset_pending=false;return r; }
uint8_t ui_event_age(void) { return state.event_age; }
bool ui_event_request(uint8_t *age) {
    if(!age || state.screen!=UI_EVENTS || !state.event_requested) return false;
    *age=state.event_age;return true;
}
uint8_t ui_channel(void) { return state.channel; }
void ui_event_result(uint8_t age,uint8_t count,res_t result,const event_t *e) {
    if(state.screen!=UI_EVENTS || age!=state.event_age || count>EVENT_SLOTS || result==RES_BUSY) return;
    state.event_requested=false;
    state.event_count=count; state.event_valid=result==RES_OK && e!=NULL;
    if(state.event_valid) state.event=*e;
}
void ui_detail_stats(temp_dC_t min,temp_dC_t max,temp_dC_t cj) { state.minimum=min;state.maximum=max;state.cj=cj; }
void ui_service_step(const char step[4]) { if(step) memcpy(state.service_step,step,4); }
void ui_alarm_snapshot(uint8_t count,fault_code_t code,uint8_t ch,uint8_t unit) {
    state.alarm_count=count;state.alarm_code=code;state.alarm_channel=ch;
    state.alarm_unit=unit;state.alarm_snapshot=true;
}
void ui_store_result(res_t r) {
    if(!state.transaction || r==RES_BUSY) return;
    state.transaction=false;
    if(r==RES_OK) {
        bool ack=state.protection_change && !state.recovering;
        home(); state.message=ack?UM_SAVED_ACK:UM_SAVED;
    } else {
        state.message=state.protection_change?UM_FAILED_PROT:UM_FAILED_INFO;
        if(state.screen==UI_SAVING) state.screen=state.recovering?UI_RECOVER:UI_CONFIRM;
    }
    state.message_ms=tick_ms(); row=0;
}
static void pin_start(bool new_pin) {
    state.pin=0;state.digit=state.position=0;state.pin_second=false;
    state.screen=new_pin?UI_NEW_PIN:UI_PIN;
}
static void pin_key(key_t key,const settings_t *cfg,uint32_t now) {
    uint8_t shift;
    if(state.locked) {
        if(now-state.lock_ms<60000u) { state.message=UM_LOCKOUT;return; }
        state.locked=false;state.attempts=0;state.message=UM_NONE;
    }
    if(key==KEY_UP) state.digit=state.digit==9?0:(uint8_t)(state.digit+1);
    if(key==KEY_DOWN) state.digit=state.digit==0?9:(uint8_t)(state.digit-1);
    if(key==KEY_ESC) { if(state.screen==UI_NEW_PIN && !state.blank) state.screen=UI_SETUP;else home();return; }
    if(key!=KEY_SET) return;
    shift=(uint8_t)(12u-4u*state.position);
    state.pin=(uint16_t)(state.pin|((uint16_t)state.digit<<shift)); state.digit=0;
    if(++state.position<4) return;
    if(state.screen==UI_PIN) {
        if(state.pin!=(state.blank?0:cfg->pin_bcd)) {
            if(++state.attempts>=3) { state.locked=true;state.lock_ms=now;state.message=UM_LOCKOUT; }
            else state.message=UM_BAD_PIN;
            state.pin=0;state.position=0;return;
        }
        state.attempts=0;state.message=UM_NONE;state.item=0;
        ui_begin(&state,cfg,state.blank);
        if(state.blank) pin_start(true); else state.screen=UI_SETUP;
    } else if(!state.pin_second) {
        if(state.blank && !state.pin) { state.message=UM_NEW_PIN;state.position=0;return; }
        state.pin_first=state.pin;state.pin_second=true;state.pin=0;state.position=0;
        state.message=UM_NONE;
    } else if(state.pin!=state.pin_first) {
        state.message=UM_PIN_MISMATCH;pin_start(true);
    } else { state.work_pin=state.pin;state.message=UM_NONE;state.item=0;state.screen=UI_SETUP; }
}
static void ask_save(const settings_t *cfg) {
    if(ui_find_diff(&state,cfg,0)) state.screen=UI_CONFIRM;
    else { state.screen=UI_SETUP;state.item=0; }
}
static void event_move(key_t key) {
    uint8_t age=state.event_age;
    if(key==KEY_DOWN && age+1<state.event_count) age++;
    if(key==KEY_UP && age) age--;
    if(age!=state.event_age) { state.event_age=age;state.event_valid=false;state.event_requested=true; }
}
static void handle(key_t key,const ui_snapshot_t *s) {
    const settings_t *cfg=s->settings;
    switch(state.screen) {
    case UI_HOME:
        if(key==KEY_DOWN) { if(state.page<3) state.page++;else { state.screen=UI_EVENTS;state.event_age=0;state.event_valid=false;state.event_requested=true; } }
        if(key==KEY_UP && state.page) state.page--;
        if(key==KEY_SET) { state.channel=(uint8_t)(state.page*6);state.screen=UI_SELECT; }
        if(key==KEY_SET_LONG) {
            if(state.transaction) { state.message=UM_BUSY;break; }
            state.blank=fault_active(s->faults,FC_G01_SETTINGS_INVALID);
            pin_start(false);
            if(state.locked && s->now_ms-state.lock_ms<60000u) state.message=UM_LOCKOUT;
        } break;
    case UI_SELECT:case UI_CHANNELS_MENU:
        if(key==KEY_UP) state.channel=(uint8_t)((state.channel+1u)==UI_CHANNELS?0:state.channel+1u);
        if(key==KEY_DOWN) state.channel=state.channel?state.channel-1:23;
        if(key==KEY_SET) { state.screen=state.screen==UI_SELECT?UI_DETAIL:UI_FIELDS;state.item=0; }
        if(key==KEY_ESC) { if(state.session) ask_save(cfg);else home(); } break;
    case UI_DETAIL:if(key==KEY_ESC) state.screen=UI_SELECT;break;
    case UI_EVENTS:if(key==KEY_ESC) home();else event_move(key);break;
    case UI_PIN:case UI_NEW_PIN:pin_key(key,cfg,s->now_ms);break;
    case UI_SETUP:
        if(key==KEY_UP) state.item=state.item?state.item-1:3;
        if(key==KEY_DOWN) state.item=(uint8_t)((state.item+1)&3u);
        if(key==KEY_ESC || (key==KEY_SET && state.item==3)) {
            if(ui_find_diff(&state,cfg,0)) state.screen=UI_CONFIRM;else home();
        } else if(key==KEY_SET) {
            if(state.item==0) state.screen=UI_CHANNELS_MENU;
            else if(state.item==1) { state.screen=UI_COMMS;state.item=0; }
            else pin_start(true);
        } break;
    case UI_FIELDS:case UI_COMMS: {
        uint8_t count=state.screen==UI_COMMS?2:7;
        if(key==KEY_UP) state.item=state.item?state.item-1:(uint8_t)(count-1);
        if(key==KEY_DOWN) state.item=(uint8_t)(state.item+1==count?0:state.item+1);
        if(key==KEY_ESC) {
            if(state.screen==UI_COMMS) { state.screen=UI_SETUP;state.item=1; }
            else state.screen=UI_CHANNELS_MENU;
        }
        if(key==KEY_SET) { state.field=(ui_field_t)(state.screen==UI_COMMS?UF_ADDRESS+state.item:state.item);ui_edit_begin(&state); }
        } break;
    case UI_EDIT:ui_edit_key(&state,key);break;
    case UI_CONFIRM:
        if(key==KEY_ESC) { home();state.message=UM_NONE; }
        else if(key==KEY_UP || key==KEY_DOWN) (void)ui_find_diff(&state,cfg,key==KEY_UP?-1:1);
        else if(key==KEY_SET) {
            if(!candidate || state.transaction) state.message=UM_BUSY;
            else { state.entry_mask=0;state.position=0;state.screen=UI_SAVING; }
        }
        /* SET_LONG returns to editing without discarding an invalid candidate. */
        else if(key==KEY_SET_LONG) { state.screen=UI_SETUP;state.item=0;state.message=UM_NONE; }
        break;
    case UI_RECOVER:
        if(key==KEY_ESC) home();
        if(key==KEY_SET) { state.reset_pending=true;state.transaction=true;state.screen=UI_SAVING;state.protection_change=false; }
        break;
    case UI_SAVING:break; /* owner transaction cannot be cancelled by a key */
    default:home();break;
    }
}
void ui_task(uint16_t budget_us) {
    ui_snapshot_t s; key_t key; ack_reason_t reason;
    if(budget_us<1000) return;
    s.settings=app_settings();s.protection=app_protection();s.output=app_output();
    s.faults=app_faults();s.scan=scan_last();s.now_ms=tick_ms();
    s.trip_latched=app_trip_bitmap();
    if(!s.settings || !s.protection || !s.output || !s.faults || !s.scan ||
       s.settings->board_type!=24 || s.settings->channel_count!=UI_CHANNELS) return;
    if(s.protection->mode==TRIPPED && state.previous_mode!=TRIPPED) {
        home();state.message=UM_NONE; /* edit and pending gestures discarded */
    }
    state.previous_mode=s.protection->mode;
    reason=app_ack_reason();
    if(reason!=state.ack_seen) ui_ack_result(reason);
    if(state.message!=UM_NONE && s.now_ms-state.message_ms>=3000u && state.message!=UM_LOCKOUT) state.message=UM_NONE;
    if(state.locked && s.now_ms-state.lock_ms>=60000u) { state.locked=false;state.attempts=0;state.message=UM_NONE; }
    if(state.screen!=UI_HOME && state.screen!=UI_SAVING && state.screen!=UI_RECOVER &&
       s.now_ms-state.activity_ms>=(state.session || state.screen==UI_PIN?300000u:60000u)) home();
    key=state.pending;state.pending=KEY_NONE;
    if(state.screen==UI_SAVING && !state.transaction) {
        res_t result;
        if(state.entry_mask==255u) {
            result=app_commit_settings(candidate);
            if(result==RES_OK) state.transaction=true;
            else { state.screen=UI_CONFIRM;state.message=result==RES_BUSY?UM_BUSY:
                state.protection_change?UM_FAILED_PROT:UM_FAILED_INFO; }
        } else {
            result=ui_prepare(&state,s.settings,candidate);
            if(result==RES_OK) state.entry_mask=255;
            else if(result!=RES_BUSY) state.screen=UI_CONFIRM;
        }
        state.message_ms=s.now_ms;
        if(state.screen==UI_SAVING) {
            memset(frame,' ',80);ui_text(frame,0,UI_STR("SAVING..."));lcd_frame(frame);
        }
        return;
    }
    if(key!=KEY_NONE) {
        state.activity_ms=s.now_ms;state.message=UM_NONE;
        handle(key,&s);state.message_ms=s.now_ms; row=0;
        keys_repeat(state.screen==UI_EDIT || state.screen==UI_PIN || state.screen==UI_NEW_PIN);
        return;
    }
    ui_render_row(&state,&s,row,frame+20u*row);
    if(++row==4) { row=0;lcd_frame(frame); }
}
