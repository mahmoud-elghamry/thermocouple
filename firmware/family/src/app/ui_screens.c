#include "app/ui.h"
#include <string.h>

UI_NO_RAM_TABLE static const char *field_text(ui_field_t f) {
    switch(f) {
    case UF_TYPE:return UI_STR("TYPE");case UF_MODE:return UI_STR("MODE");
    case UF_NAME:return UI_STR("NAME");case UF_ALARM:return UI_STR("ALARM");
    case UF_TRIP:return UI_STR("TRIP");case UF_BAND:return UI_STR("BAND");
    case UF_LIMIT:return UI_STR("PROBE LIMIT");case UF_ADDRESS:return UI_STR("ADDRESS");
    case UF_BAUD:return UI_STR("BAUD");default:return UI_STR("PIN");
    }
}
UI_NO_RAM_TABLE static const char *message_text(ui_message_t m) {
    switch(m) {
    case UM_BAD_PIN:return UI_STR("WRONG PIN");case UM_LOCKOUT:return UI_STR("LOCKED 60s");
    case UM_PIN_MISMATCH:return UI_STR("PIN MISMATCH");case UM_NEW_PIN:return UI_STR("CHANGE DEFAULT PIN");
    case UM_INVALID:return UI_STR("INVALID SETTINGS");case UM_ORDER:return UI_STR("ALARM MUST BE < TRIP");
    case UM_REENTER:return UI_STR("REENTER AL/TR/LIMIT");case UM_BUSY:return UI_STR("SAVE BUSY - RETRY");
    case UM_FAILED_PROT:return UI_STR("SAVE FAILED G02");case UM_FAILED_INFO:return UI_STR("SAVE FAILED G13");
    case UM_SAVED:return UI_STR("SAVED OK");case UM_SAVED_ACK:return UI_STR("SAVED OK - PRESS ACK");
    case UM_STALE:return UI_STR("SETTINGS CHANGED");case UM_OFF:return UI_STR("CHANNEL OFF");
    case UM_RANGE:return UI_STR("VALUE OUT OF RANGE");
    case UM_R1:return UI_STR("R1 RELEASE ACK KEY");case UM_R2:return UI_STR("R2 WAIT FOR SCAN");
    case UM_R3:return UI_STR("R3 FAULT");case UM_R4:return UI_STR("R4 CH    HOT/FAULT");
    case UM_R5:return UI_STR("R5 SETTINGS");case UM_R6:return UI_STR("R6 RELAY CHECK");
    default:return UI_STR("");
    }
}
static char type_letter(uint8_t type) { return type==1?'K':type==2?'J':type==3?'P':' '; }
static void fault_text(char *out,uint8_t offset,fault_code_t code,uint8_t unit) {
    uint8_t n=(uint8_t)code;
    out[offset]=n>=41?'C':n>=21?'B':'G';
    if(n>=41) n-=40;else if(n>=21) n-=20;
    ui_number(out+offset+1,2,n,true);
    if(code>=FC_B01_ADC_ID && code<=FC_B15_ADC_RESET) {
        ui_text(out,(uint8_t)(offset+4),UI_STR("BANK"));
        if(offset+9<20) out[offset+9]=(char)('A'+unit);
        if(code==FC_B06_REF) ui_text(out,(uint8_t)(offset+11),UI_STR("REF"));
    }
}
static void status(const ui_state_t *u,const ui_snapshot_t *s,char *out) {
    const prot_state_t *p=s->protection; uint8_t ch,count=0,newest=0;
    if(p->mode==SERVICE) { ui_text(out,0,UI_STR("SERVICE MODE"));memcpy(out+16,u->service_step,4);return; }
    if(p->mode==CONFIG_LOCK) {
        ui_text(out,0,fault_active(s->faults,FC_G01_SETTINGS_INVALID)?UI_STR("LOCKED: SETUP"):UI_STR("LOCKED: CALIBRATE"));return;
    }
    if(p->mode==TRIPPED) {
        ui_text(out,0,UI_STR("TRIP"));
        if(p->first.valid && p->first.channel>0 && p->first.channel<=UI_CHANNELS) {
            ui_number(out+5,2,p->first.channel,true);ui_name(out+8,s->settings->ch[p->first.channel-1].name);
        } else fault_text(out,5,p->first.valid?p->first.code:FC_G04_INTERNAL,p->first.unit);
        return;
    }
    if(p->mode==START_LATCHED) { ui_text(out,0,UI_STR("START: ACK REQUIRED"));return; }
    if(p->mode!=RUN) { ui_text(out,0,UI_STR("TRIP G04"));return; }
    for(ch=0;ch<UI_CHANNELS;ch++) if(s->settings->ch[ch].type!=CH_TYPE_OFF && p->alarm_latch[ch]) count++;
    if(u->alarm_snapshot) { count=u->alarm_count;newest=u->alarm_channel; }
    if(count || s->output->alarm_active) {
        ui_text(out,0,UI_STR("ALARM"));ui_number(out+6,2,count?count:1,false);
        if(u->alarm_snapshot && newest>0 && newest<=UI_CHANNELS) {
            ui_number(out+10,2,newest,true);ui_name(out+13,s->settings->ch[newest-1].name);
        } else if(u->alarm_snapshot && u->alarm_code!=FC_NONE) fault_text(out,10,u->alarm_code,u->alarm_unit);
        else ui_text(out,10,UI_STR("FAULT"));
    } else if(fault_active(s->faults,FC_B12_CJ_ONE)) ui_text(out,0,UI_STR("RUN  DEGRADED CJ"));
    else {
        uint32_t scan=s->scan->scan_no;
        /* Display modulo 100000 without a general divide. */
        if(scan>=UINT32_C(3200000000)) scan-=UINT32_C(3200000000);
        if(scan>=UINT32_C(1600000000)) scan-=UINT32_C(1600000000);
        if(scan>=800000000UL) scan-=800000000UL;
        if(scan>=400000000UL) scan-=400000000UL;
        if(scan>=200000000UL) scan-=200000000UL;
        if(scan>=100000000UL) scan-=100000000UL;
        if(scan>=50000000UL) scan-=50000000UL;
        if(scan>=25000000UL) scan-=25000000UL;
        if(scan>=12800000UL) scan-=12800000UL;
        if(scan>=6400000UL) scan-=6400000UL;
        if(scan>=3200000UL) scan-=3200000UL;
        if(scan>=1600000UL) scan-=1600000UL;
        if(scan>=800000UL) scan-=800000UL;
        if(scan>=400000UL) scan-=400000UL;
        if(scan>=200000UL) scan-=200000UL;
        if(scan>=100000UL) scan-=100000UL;
        ui_text(out,0,UI_STR("RUN OK"));out[14]='#';ui_number(out+15,5,(int32_t)scan,true);
    }
}
static const char *measurement(const result_t *r,uint32_t scan) {
    if(r->flags&MEAS_OPEN) return UI_STR("OPEN");
    if(r->flags&MEAS_RANGE) return UI_STR("RANGE");
    if(r->flags&MEAS_CM_FAIL) return UI_STR("CM FAIL");
    if(r->flags&MEAS_SHORTED) return UI_STR("SHORTED");
    if(r->flags&MEAS_OVUV) return UI_STR("OV/UV");
    if(r->flags&MEAS_COLD) return UI_STR("COLD");
    if(!(r->flags&MEAS_VALID) || r->temp_dC==TEMP_DC_INVALID || r->scan_no!=scan) return UI_STR("----");
    return NULL;
}
static void home_row(const ui_state_t *u,const ui_snapshot_t *s,uint8_t row,char *out) {
    uint8_t i;
    if(row==0) { status(u,s,out);return; }
    for(i=0;i<2;i++) {
        uint8_t ch=(uint8_t)(u->page*6u+(row-1u)*2u+i),offset=(uint8_t)(10u*i);
        const chan_cfg_t *c; const result_t *r; const char *error; char marker=' ';
        if(ch>=UI_CHANNELS) continue;
        c=&s->settings->ch[ch];r=&s->scan->meas[ch];
        error=measurement(r,s->scan->scan_no);
        ui_number(out+offset,2,ch+1,true);out[offset+7]=type_letter((uint8_t)c->type);
        if(fault_active(s->faults,FC_G01_SETTINGS_INVALID)) ui_text(out,offset+3,UI_STR("----"));
        else if(c->type==CH_TYPE_OFF) { ui_text(out,offset+3,UI_STR("off "));marker='-'; }
        else {
            if(error) {
                /* Home has four columns; detail carries the full fault text. */
                uint8_t j; for(j=0;j<4;j++) {
#ifdef __AVR__
                    char v=(char)pgm_read_byte(error+j);
#else
                    char v=error[j];
#endif
                    if(!v) break;
                    out[offset+3+j]=v;
                }
                marker='?';
            } else ui_number(out+offset+3,4,ui_whole(r->temp_dC),false);
            if(s->protection->trip_seen[ch]) marker='#';
            else if(marker!='?' && s->protection->alarm_latch[ch]) marker='!';
            else if(marker==' ' && c->mode==CH_MODE_ALARM_ONLY) marker='a';
        }
        out[offset+8]=marker;
    }
}
static void detail_row(const ui_state_t *u,const ui_snapshot_t *s,uint8_t row,char *out) {
    uint8_t ch=u->channel<UI_CHANNELS?u->channel:0;
    const chan_cfg_t *c=&s->settings->ch[ch];const result_t *r=&s->scan->meas[ch];
    const char *error=measurement(r,s->scan->scan_no);
    switch(row) {
    case 0:ui_number(out,2,ch+1,true);ui_name(out+3,c->name);out[10]=type_letter((uint8_t)c->type);
        ui_text(out,13,c->type==CH_TYPE_OFF?UI_STR("OFF"):c->mode==CH_MODE_TRIP?UI_STR("TRIP"):UI_STR("AL ONLY"));break;
    case 1:
        if(c->type==CH_TYPE_OFF) ui_text(out,1,UI_STR("off"));
        else if(error) ui_text(out,0,error);
        else { ui_number(out,4,ui_whole(r->temp_dC),false);out[4]='C'; }
        ui_text(out,7,UI_STR("CJ"));
        if(u->cj==TEMP_DC_INVALID) ui_text(out,11,UI_STR("----"));
        else { int16_t whole=ui_whole(u->cj),fraction=(int16_t)(u->cj-whole*10);
            ui_number(out+10,4,whole,false);if(u->cj<0 && whole==0) out[12]='-';
            out[14]='.';out[15]=(char)('0'+(fraction<0?-fraction:fraction));out[16]='C'; }
        break;
    case 2:ui_text(out,0,UI_STR("AL"));ui_number(out+3,4,ui_whole(c->alarm_dC),false);
        ui_text(out,8,UI_STR("TR"));ui_number(out+11,4,ui_whole(c->trip_dC),false);
        out[16]='B';ui_number(out+18,2,c->band_C,false);break;
    default: {
        uint8_t width=(u->minimum>=10000 || u->maximum>=10000 || u->minimum<=-1000)?4:3;
        uint8_t max_at=(uint8_t)(5+width);
        ui_text(out,0,UI_STR("MIN"));ui_text(out,max_at,UI_STR("MAX"));
        if(u->minimum==TEMP_DC_INVALID) ui_text(out,4,UI_STR("---"));else ui_number(out+4,width,ui_whole(u->minimum),false);
        if(u->maximum==TEMP_DC_INVALID) ui_text(out,max_at+4,UI_STR("---"));else ui_number(out+max_at+4,width,ui_whole(u->maximum),false);
        break;
        }
    }
}
static void event_time(char *out,uint32_t seconds) {
    uint16_t hours=0,days=0;uint8_t minutes=0;
    if(seconds>=360000UL) {
        while(seconds>=8640000UL) { seconds-=8640000UL;days+=100; }
        while(seconds>=864000UL) { seconds-=864000UL;days+=10; }
        while(seconds>=86400UL) { seconds-=86400UL;days++; }
        while(seconds>=3600UL) { seconds-=3600UL;hours++; }
        ui_number(out,3,days,false);out[3]='d';ui_number(out+5,2,hours,true);out[7]='h';return;
    }
    while(seconds>=36000UL) { seconds-=36000UL;hours+=10; }
    while(seconds>=3600UL) { seconds-=3600UL;hours++; }
    while(seconds>=600UL) { seconds-=600UL;minutes+=10; }
    while(seconds>=60UL) { seconds-=60UL;minutes++; }
    ui_number(out,2,hours,false);out[2]=':';ui_number(out+3,2,minutes,true);out[5]=':';ui_number(out+6,2,(int32_t)seconds,true);
}
UI_NO_RAM_TABLE static const char *event_name(event_type_t type) {
    switch(type) {
    case EV_TRIP:return UI_STR("TRIP");case EV_ALARM:return UI_STR("ALARM");case EV_FAULT:return UI_STR("FAULT");
    case EV_ACK:return UI_STR("ACK");case EV_POWER_UP:return UI_STR("POWER UP");case EV_PIN_RESET:return UI_STR("PIN RESET");
    case EV_SETTINGS_CHANGED:return UI_STR("SETTINGS");case EV_NAME_CHANGED:return UI_STR("NAME");
    case EV_SERVICE_ENTRY:return UI_STR("SERVICE");default:return UI_STR("CALIBRATION");
    }
}
static void events_row(const ui_state_t *u,const ui_snapshot_t *s,uint8_t row,char *out) {
    const event_t *e=&u->event;
    if(row==0) { ui_text(out,0,UI_STR("EVENTS"));ui_number(out+7,2,u->event_count?u->event_age+1:0,false);out[9]='/';ui_number(out+10,2,u->event_count,false); }
    else if(row==3) {
        if(u->event_valid && e->power_cycles>=100) { ui_text(out,0,UI_STR("T"));event_time(out+2,e->uptime_s); }
        else ui_text(out,0,UI_STR("ESC=back UP/DN=scroll"));
    }
    else if(!u->event_valid) ui_text(out,0,UI_STR("--"));
    else if(row==1) {
        ui_text(out,0,event_name(e->type));
        if(e->channel && e->channel<=UI_CHANNELS) {
            ui_number(out+5,2,e->channel,true);ui_name(out+8,s->settings->ch[e->channel-1].name);
            ui_number(out+14,4,ui_whole(e->value_dC),false);out[18]='C';
        } else if(e->code!=FC_NONE) fault_text(out,6,e->code,e->unit?e->unit-1:0);
    } else {
        out[0]='>';ui_number(out+1,4,ui_whole(e->threshold_dC),false);
        ui_text(out,6,UI_STR("PC"));ui_number(out+9,5,e->power_cycles,false);
        /* Preserve the full 16-bit PC; long PCs use the footer for uptime. */
        if(e->power_cycles<100) { memset(out+8,' ',12);ui_number(out+8,2,e->power_cycles,false);out[11]='T';event_time(out+12,e->uptime_s); }
    }
}
static int16_t old_value(const chan_cfg_t *c,ui_field_t field) {
    switch(field) {
    case UF_TYPE:return (int16_t)c->type;case UF_MODE:return (int16_t)c->mode;
    case UF_ALARM:return ui_whole(c->alarm_dC);case UF_TRIP:return ui_whole(c->trip_dC);
    case UF_BAND:return c->band_C;default:return ui_whole(c->probe_limit_dC);
    }
}
static int16_t new_value(const ui_chan_t *c,ui_field_t field) {
    switch(field) {
    case UF_TYPE:return c->type&3u;case UF_MODE:return c->mode;
    case UF_ALARM:return ui_whole(c->alarm);case UF_TRIP:return ui_whole(c->trip);
    case UF_BAND:return c->band;default:return ui_whole(c->limit);
    }
}
static void difference(const ui_state_t *u,const ui_snapshot_t *s,char *out) {
    uint8_t ch=0,f=u->diff;
    if(f>=168) {
        ui_text(out,0,f==168?UI_STR("ADDRESS"):f==169?UI_STR("BAUD"):UI_STR("PIN CHANGED"));
        if(f==168) { ui_number(out+8,3,s->settings->address,false);ui_text(out,12,UI_STR("->"));ui_number(out+15,3,u->address,false); }
        if(f==169) { ui_number(out+5,5,s->settings->baud?19200:9600,false);ui_text(out,10,UI_STR("->"));ui_number(out+13,5,u->baud?19200:9600,false); }
        return;
    }
    while(f>=7) { f-=7;ch++; }
    ui_text(out,0,UI_STR("CH"));ui_number(out+2,2,ch+1,true);ui_text(out,5,field_text((ui_field_t)f));
    if(f==UF_NAME) {
        /* Six old and six new characters need the compact channel prefix. */
        memset(out,' ',20);ui_number(out,2,ch+1,true);
        ui_name(out+3,s->settings->ch[ch].name);ui_text(out,9,UI_STR(" -> "));
        ui_name(out+13,u->work[ch].name);return;
    }
    if(f==UF_TYPE) {
        uint8_t old=(uint8_t)s->settings->ch[ch].type,type=u->work[ch].type&3u;
        ui_text(out,10,old==0?UI_STR("OFF"):old==1?UI_STR("K"):UI_STR("J"));
        ui_text(out,14,UI_STR("->"));ui_text(out,17,type==0?UI_STR("OFF"):type==1?UI_STR("K"):UI_STR("J"));return;
    }
    /* Compact labels leave room for four-digit old/new values. */
    if(f==UF_LIMIT) { memset(out+5,' ',15);ui_text(out,5,UI_STR("LIM")); }
    ui_number(out+9,4,old_value(&s->settings->ch[ch],(ui_field_t)f),false);
    ui_text(out,13,UI_STR(" ->"));ui_number(out+16,4,new_value(&u->work[ch],(ui_field_t)f),false);
}
void ui_render_row(const ui_state_t *u,const ui_snapshot_t *s,uint8_t row,char out[20]) {
    memset(out,' ',20);
    if(!u || !s || !s->settings || !s->protection || !s->output || !s->faults || !s->scan || row>3) return;
    if(row==3 && u->message!=UM_NONE) {
        ui_text(out,0,message_text(u->message));
        if(u->message==UM_R4) ui_number(out+6,2,s->output->refusal_channel,true);
        if(u->message==UM_R3) { uint8_t unit=0;fault_code_t code=fault_first_trip(s->faults,&unit);fault_text(out,9,code,unit); }
        return;
    }
    switch(u->screen) {
    case UI_HOME:home_row(u,s,row,out);break;
    case UI_SELECT:case UI_CHANNELS_MENU:
        if(row==0) { if(u->screen==UI_SELECT) status(u,s,out);else ui_text(out,0,UI_STR("CHANNELS")); }
        if(row==1) ui_text(out,0,UI_STR("CHOOSE CHANNEL"));
        if(row==2) { ui_number(out,2,u->channel+1,true);if(u->channel<UI_CHANNELS) ui_name(out+3,u->session?u->work[u->channel].name:s->settings->ch[u->channel].name); }
        if(row==3) ui_text(out,0,UI_STR("SET=enter ESC=back"));
        break;
    case UI_DETAIL:detail_row(u,s,row,out);break;
    case UI_EVENTS:events_row(u,s,row,out);break;
    case UI_PIN:case UI_NEW_PIN:
        if(row==0) ui_text(out,0,u->screen==UI_PIN?UI_STR("SETUP PIN"):u->pin_second?UI_STR("REPEAT NEW PIN"):UI_STR("NEW PIN"));
        if(row==1) { uint8_t i;for(i=0;i<4;i++) out[6+i]=i<u->position?'*':i==u->position?(char)('0'+u->digit):'_'; }
        if(row==2) ui_text(out,0,UI_STR("UP/DN=digit SET=next"));
        if(row==3) ui_text(out,0,UI_STR("ESC=cancel"));
        break;
    case UI_SETUP:
        if(row==0) ui_text(out,0,UI_STR("SETUP"));
        if(row==1) ui_text(out,0,u->item==0?UI_STR(">1 CHANNELS"):u->item==1?UI_STR(">2 COMMS"):u->item==2?UI_STR(">3 PIN"):UI_STR(">4 EXIT"));
        if(row==3) ui_text(out,0,UI_STR("UP/DN SET=enter"));
        break;
    case UI_FIELDS:case UI_COMMS:case UI_EDIT: {
        ui_field_t f=u->screen==UI_EDIT?u->field:(ui_field_t)(u->screen==UI_COMMS?UF_ADDRESS+u->item:u->item);
        if(row==0) { if(f<UF_ADDRESS) { ui_text(out,0,UI_STR("CHANNEL"));ui_number(out+8,2,u->channel+1,true); }else ui_text(out,0,UI_STR("COMMS")); }
        if(row==1) ui_text(out,0,field_text(f));
        if(row==2 && u->channel<UI_CHANNELS) {
            int16_t v=u->screen==UI_EDIT?u->edit_value:new_value(&u->work[u->channel],f);
            if(f==UF_NAME) { ui_name(out,u->screen==UI_EDIT?u->edit_name:u->work[u->channel].name);out[8]=(char)('1'+u->position); }
            else if(f==UF_TYPE) ui_text(out,0,v==0?UI_STR("OFF"):v==1?UI_STR("K"):UI_STR("J"));
            else if(f==UF_MODE) ui_text(out,0,v==0?UI_STR("TRIP"):UI_STR("ALARM ONLY"));
            else if(f==UF_ADDRESS) ui_number(out,3,u->screen==UI_EDIT?v:u->address,false);
            else if(f==UF_BAUD) ui_number(out,5,(u->screen==UI_EDIT?v:u->baud)?19200:9600,false);
            else ui_number(out,4,v,false);
        }
        if(row==3) ui_text(out,0,u->screen==UI_EDIT?UI_STR("SET=accept ESC=cancel"):UI_STR("SET=edit ESC=back"));
        } break;
    case UI_CONFIRM:
        if(row==0) ui_text(out,0,UI_STR("SAVE CHANGES?"));
        if(row==1) difference(u,s,out);
        if(row==2) ui_text(out,0,u->message!=UM_NONE?UI_STR("HOLD SET=edit again"):
            u->protection_change?UI_STR("CONTACT WILL OPEN"):UI_STR("NO EFFECT ON RUN"));
        if(row==3) ui_text(out,0,UI_STR("SET=save ESC=discard"));
        break;
    case UI_SAVING:if(row==0) ui_text(out,0,UI_STR("SAVING..."));break;
    case UI_RECOVER:if(row==0) ui_text(out,0,UI_STR("PIN RESET? SET=YES"));if(row==3) ui_text(out,0,UI_STR("ESC=cancel"));break;
    default:if(row==0) ui_text(out,0,UI_STR("UI ERROR"));break;
    }
}
void ui_render(const ui_state_t *u,const ui_snapshot_t *s,char out[80]) {
    uint8_t row; for(row=0;row<4;row++) ui_render_row(u,s,row,out+20u*row);
}
