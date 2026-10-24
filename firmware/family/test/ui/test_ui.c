#include "fake_ui.h"
#include <stdio.h>
#include <string.h>
static unsigned checks,failures;
#define CHECK(x) do { checks++; if(!(x)) { failures++; printf("FAIL %s:%u: %s\n",__FILE__,(unsigned)__LINE__,#x); } } while(0)
static bool has(const char *s) {
    char f[81]; memcpy(f,fake_frame,80); f[80]=0; return strstr(f,s)!=NULL;
}
static void times(key_t k,unsigned n) { while(n--) fake_key(k); }
static void pin(uint16_t p) {
    int shift; for(shift=12;shift>=0;shift-=4) { times(KEY_UP,(p>>shift)&15u); fake_key(KEY_SET); }
}
static void setup(void) { fake_key(KEY_SET_LONG); pin(0x1234); CHECK(has("SETUP")); }
static void field(unsigned n) { fake_key(KEY_SET); fake_key(KEY_SET); times(KEY_DOWN,n); fake_key(KEY_SET); }
static void confirm(void) { fake_key(KEY_ESC); fake_key(KEY_ESC); CHECK(has("SAVE CHANGES?")); }
static void test_navigation(void) {
    unsigned i; settings_t before; prot_state_t prot;
    fake_reset(false); CHECK(has("RUN OK")); CHECK(has("#01234")); CHECK(has("01  512K"));
    before=fake_settings; prot=fake_protection;
    times(KEY_DOWN,3); CHECK(has("19  512K")); fake_key(KEY_DOWN); CHECK(has("EVENTS"));
    fake_key(KEY_ESC); CHECK(has("RUN OK")); times(KEY_UP,3); fake_key(KEY_SET); CHECK(has("CHOOSE CHANNEL"));
    times(KEY_UP,2); fake_key(KEY_SET); CHECK(has("03 CYL3B")); CHECK(has("CJ"));
    ui_detail_stats(4980,5160,312); fake_pump(); CHECK(has("MIN 498 MAX 516")); CHECK(has("31.2C"));
    fake_key(KEY_ESC); fake_ms+=60001; fake_pump(); CHECK(has("RUN OK"));
    CHECK(!ui_key(KEY_ACK)); CHECK(memcmp(&prot,&fake_protection,sizeof prot)==0);
    CHECK(memcmp(&before,&fake_settings,sizeof before)==0); CHECK(fake_commits==0);
    for(i=0;i<1000;i++) ui_task(0); CHECK(fake_commits==0);
    fake_key(KEY_SET); fake_ms+=60001; fake_pump(); CHECK(has("RUN OK"));
}
static void test_pin(void) {
    unsigned i; fake_reset(false);
    for(i=0;i<3;i++) { fake_key(KEY_SET_LONG); pin(0); CHECK(has(i==2?"LOCKED 60s":"WRONG PIN")); fake_key(KEY_ESC); }
    fake_key(KEY_SET_LONG); CHECK(has("LOCKED 60s"));
    fake_ms+=60001; fake_pump(); setup();
    fake_ms+=60001; fake_pump(); CHECK(has("SETUP"));
    fake_ms+=300001; fake_pump(); CHECK(has("RUN OK"));
    fake_reset(false); setup(); times(KEY_DOWN,2); fake_key(KEY_SET);
    pin(0x2468); CHECK(has("REPEAT NEW PIN")); pin(0x2467); CHECK(has("PIN MISMATCH"));
    pin(0x2468); pin(0x2468); times(KEY_DOWN,3); fake_key(KEY_SET);
    CHECK(has("SAVE CHANGES?")); fake_key(KEY_SET); CHECK(has("SAVING"));
    CHECK(fake_candidate.pin_bcd==0x2468); fake_finish(RES_OK); CHECK(has("SAVED OK"));
}
static void test_edits(void) {
    fake_reset(false); setup(); field(UF_TRIP); CHECK(fake_repeat);
    fake_key(KEY_DOWN); fake_key(KEY_SET); confirm(); CHECK(has("CONTACT WILL OPEN")); CHECK(has("520 -> 519"));
    CHECK(fake_settings.ch[0].trip_dC==5200); fake_key(KEY_SET); CHECK(has("SAVING"));
    CHECK(fake_commits==1); CHECK(fake_candidate.ch[0].trip_dC==5190);
    fake_pump(); CHECK(!has("SAVED OK")); fake_finish(RES_OK); CHECK(has("SAVED OK - PRESS ACK"));
    fake_reset(false); setup(); field(UF_NAME); fake_key(KEY_UP); times(KEY_SET,6); confirm();
    CHECK(has("NO EFFECT ON RUN")); fake_key(KEY_ESC); CHECK(fake_commits==0);
    fake_reset(false); setup(); field(UF_MODE); fake_key(KEY_UP); fake_key(KEY_SET); confirm();
    fake_key(KEY_SET); CHECK(fake_candidate.ch[0].mode==CH_MODE_ALARM_ONLY);
    fake_reset(false); setup(); field(UF_BAND); times(KEY_DOWN,10); fake_key(KEY_SET); confirm();
    fake_key(KEY_SET); CHECK(fake_candidate.ch[0].band_C==2);
    fake_reset(false); setup(); field(UF_LIMIT); fake_key(KEY_UP); fake_key(KEY_SET); confirm();
    fake_key(KEY_SET); CHECK(fake_candidate.ch[0].probe_limit_dC==10100);
    fake_reset(false); setup(); field(UF_ALARM); fake_key(KEY_DOWN); fake_key(KEY_SET); confirm();
    fake_key(KEY_SET); CHECK(fake_candidate.ch[0].alarm_dC==4790);
}
static void test_type_and_invalid(void) {
    fake_reset(false); setup(); field(UF_TYPE); fake_key(KEY_UP); fake_key(KEY_SET); confirm();
    fake_key(KEY_SET); CHECK(has("REENTER AL/TR/LIMIT")); CHECK(fake_commits==0);
    fake_key(KEY_ESC); CHECK(fake_settings.ch[0].type==CH_TYPE_K);
    fake_reset(false); setup(); field(UF_TYPE); fake_key(KEY_DOWN); fake_key(KEY_SET); confirm();
    fake_key(KEY_SET); CHECK(fake_candidate.ch[0].type==CH_TYPE_OFF);
    CHECK(fake_candidate.ch[0].mode==CH_MODE_TRIP && fake_candidate.ch[0].band_C==2);
    CHECK(fake_candidate.ch[0].trip_dC==0 && fake_candidate.ch[0].probe_limit_dC==0);
    CHECK(fake_candidate.ch[0].type_epoch==1); fake_finish(RES_OK); CHECK(has("off"));
    fake_reset(false); fake_settings.ch[0].alarm_dC=5200; setup(); field(UF_NAME);
    fake_key(KEY_UP); times(KEY_SET,6); confirm(); fake_key(KEY_SET);
    CHECK(has("ALARM MUST BE < TRIP")); CHECK(fake_commits==0);
    fake_reset(false); setup(); field(UF_TRIP); fake_key(KEY_DOWN); fake_key(KEY_ESC);
    fake_key(KEY_ESC); fake_key(KEY_ESC); CHECK(!has("SAVE CHANGES?")); CHECK(fake_commits==0);
}
static void test_comms_and_results(void) {
    fake_reset(false); setup(); fake_key(KEY_DOWN); fake_key(KEY_SET); fake_key(KEY_SET);
    times(KEY_UP,300); fake_key(KEY_SET); fake_key(KEY_DOWN); fake_key(KEY_SET); fake_key(KEY_UP); fake_key(KEY_SET);
    fake_key(KEY_ESC); times(KEY_DOWN,2); fake_key(KEY_SET); CHECK(has("NO EFFECT ON RUN"));
    fake_commit_result=RES_BUSY; fake_key(KEY_SET); CHECK(has("SAVE BUSY")); CHECK(fake_commits==1);
    fake_commit_result=RES_OK; fake_key(KEY_SET); CHECK(fake_candidate.address==247 && fake_candidate.baud==1);
    ui_store_result(RES_BUSY); fake_pump(); CHECK(has("SAVING"));
    fake_finish(RES_ERR_READBACK); CHECK(has("SAVE FAILED G13"));
    fake_key(KEY_SET); fake_finish(RES_OK); CHECK(has("SAVED OK"));
    fake_reset(false); setup(); field(UF_TRIP); fake_key(KEY_DOWN); fake_key(KEY_SET); confirm();
    fake_commit_result=RES_ERR_READBACK; fake_key(KEY_SET); CHECK(has("SAVE FAILED G02"));
}
static void test_trip_and_timeout(void) {
    fake_reset(false); setup(); field(UF_TRIP); fake_key(KEY_DOWN);
    fake_protection.mode=TRIPPED; fake_protection.first.valid=true; fake_protection.first.channel=3;
    fake_protection.first.code=FC_C10_OVER_TRIP; fake_pump(); CHECK(has("TRIP 03 CYL3B")); CHECK(!fake_repeat);
    CHECK(fake_commits==0); setup(); CHECK(has("SETUP"));
    fake_protection.first.channel=4; fake_pump(); CHECK(has("SETUP"));
    fake_ms+=300001; fake_pump(); CHECK(has("TRIP"));
    fake_reset(false); setup(); field(UF_TRIP); fake_key(KEY_DOWN); fake_key(KEY_SET);
    fake_settings.sequence++; confirm(); fake_key(KEY_SET); CHECK(has("SETTINGS CHANGED")); CHECK(fake_commits==0);
}
static void test_commission_recovery(void) {
    unsigned i;
    fake_reset(true); CHECK(has("LOCKED: SETUP")); CHECK(has("----"));
    fake_key(KEY_SET_LONG); pin(0); CHECK(has("NEW PIN")); pin(0); CHECK(has("CHANGE DEFAULT PIN"));
    pin(0x1234); pin(0x1234); CHECK(has("SETUP"));
    field(UF_TYPE); fake_key(KEY_UP); fake_key(KEY_SET);
    times(KEY_DOWN,UF_LIMIT); fake_key(KEY_SET); fake_key(KEY_UP); fake_key(KEY_SET);
    times(KEY_UP,UF_LIMIT-UF_ALARM); fake_key(KEY_SET); fake_key(KEY_UP); fake_key(KEY_SET);
    fake_key(KEY_DOWN); fake_key(KEY_SET); times(KEY_UP,2); fake_key(KEY_SET); confirm();
    fake_key(KEY_SET); CHECK(fake_commits==1); CHECK(set_validate(&fake_candidate)==RES_OK);
    for(i=1;i<24;i++) CHECK(fake_candidate.ch[i].type==CH_TYPE_OFF && fake_candidate.ch[i].band_C==2);
    fake_finish(RES_OK); fault_clear(&fake_faults,FC_G01_SETTINGS_INVALID,0);
    (void)fault_raise(&fake_faults,FC_G10_CALIBRATION,0); fake_pump(); CHECK(has("LOCKED: CALIBRATE"));
    /* Settings validity, not even a stale G01 diagnostic, selects the editor. */
    (void)fault_raise(&fake_faults,FC_G01_SETTINGS_INVALID,0);
    fake_pump();CHECK(has("LOCKED: CALIBRATE"));
    fake_key(KEY_SET_LONG); pin(0); CHECK(has("WRONG PIN"));
    pin(0x1234); CHECK(ui_current_screen()==UI_SETUP);
    fake_key(KEY_SET); fake_key(KEY_SET); CHECK(has("K"));
    fake_key(KEY_ESC); fake_key(KEY_ESC); CHECK(fake_commits==1);
    fake_reset(false); ui_pin_recovery(); fake_pump(); CHECK(has("PIN RESET?"));
    fake_key(KEY_SET); CHECK(ui_take_pin_reset()); CHECK(!ui_take_pin_reset()); CHECK(fake_commits==0);
    ui_store_result(RES_OK); fake_pump(); CHECK(has("SAVED OK"));
}
static void test_events(void) {
    event_t e; memset(&e,0,sizeof e); e.type=EV_TRIP; e.channel=3; e.value_dC=5230; e.threshold_dC=5200;
    e.power_cycles=18; e.uptime_s=15129;
    fake_reset(false); times(KEY_DOWN,4); CHECK(ui_event_age()==0);
    { uint8_t age=255;CHECK(ui_event_request(&age) && age==0); }
    ui_event_result(0,32,RES_OK,&e); fake_pump(); CHECK(has("EVENTS  1/32")); CHECK(has("TRIP 03 CYL3B")); CHECK(has("4:12:09"));
    { uint8_t age;CHECK(!ui_event_request(&age)); }
    fake_key(KEY_DOWN); CHECK(ui_event_age()==1); ui_event_result(0,32,RES_OK,&e); fake_pump(); CHECK(!has("523C"));
    ui_event_result(1,32,RES_ERR_CRC,NULL); fake_pump(); CHECK(has("--"));
    e.uptime_s=360000; ui_event_result(1,32,RES_OK,&e); fake_pump(); CHECK(has("4d 04h"));
    fake_key(KEY_UP); CHECK(ui_event_age()==0); fake_key(KEY_ESC); CHECK(has("RUN OK"));
}
static void test_messages_and_edges(void) {
    unsigned i; static const char *const messages[]={"R1 RELEASE ACK KEY","R2 WAIT FOR SCAN","R3 FAULT G03",
        "R4 CH 03 HOT/FAULT","R5 SETTINGS","R6 RELAY CHECK"};
    fake_reset(false);fake_output.refusal_channel=3;(void)fault_raise(&fake_faults,FC_G03_FLASH_CRC,0);
    for(i=0;i<6;i++) {
        fake_output.refusal_channel=3; fake_ack((ack_reason_t)(ACK_R1_RELEASE+i));
        fake_output.refusal_channel=0;fake_pump();CHECK(has(messages[i]));
        if(i==ACK_R4_CHANNEL-ACK_R1_RELEASE) {
            fake_ack(ACK_NONE);fake_pump();CHECK(has(messages[i]));
        }
        fake_ms+=3001;fake_pump();CHECK(!has(messages[i]));
        fake_output.refusal_channel=3; fake_ack((ack_reason_t)(ACK_R1_RELEASE+i));
        fake_output.refusal_channel=0;fake_pump();CHECK(has(messages[i]));
    }
    fake_reset(false);setup();field(UF_TRIP);fake_key(KEY_DOWN);fake_key(KEY_SET);confirm();
    CHECK(ui_key(KEY_SET));ui_task(999);CHECK(fake_commits==0);ui_task(1000); /* begin preparation */
    fake_settings.sequence++;fake_pump();CHECK(has("SETTINGS CHANGED"));CHECK(fake_commits==0);
    fake_reset(false);setup();field(UF_TRIP);fake_key(KEY_DOWN);fake_key(KEY_SET);confirm();
    fake_key(KEY_SET);CHECK(has("SAVING"));fake_protection.mode=TRIPPED;fake_pump();CHECK(has("TRIP"));
    fake_key(KEY_SET_LONG);CHECK(has("SAVE BUSY"));fake_finish(RES_OK);CHECK(has("SAVED OK"));
    fake_reset(false);ui_bind_candidate(NULL);setup();field(UF_TRIP);fake_key(KEY_DOWN);fake_key(KEY_SET);confirm();
    fake_key(KEY_SET);CHECK(has("SAVE BUSY"));CHECK(fake_commits==0);
    fake_reset(false);ui_pin_recovery();fake_key(KEY_ESC);CHECK(!ui_take_pin_reset());CHECK(has("RUN OK"));
}
static void test_display_values(void) {
    ui_state_t u;ui_snapshot_t s;char f[81];uint32_t scans[]={0,99999,100000,25000000,12800000,UINT32_MAX};unsigned i;
    fake_reset(false);memset(&u,0,sizeof u);memset(&s,0,sizeof s);
    s.settings_valid=true;s.settings=&fake_settings;s.protection=&fake_protection;s.output=&fake_output;s.scan=&fake_scan;s.faults=&fake_faults;
    for(i=0;i<sizeof scans/sizeof scans[0];i++) {
        char wanted[7];fake_scan.scan_no=scans[i];ui_render(&u,&s,f);f[80]=0;
        (void)snprintf(wanted,sizeof wanted,"#%05lu",(unsigned long)(scans[i]%100000));CHECK(strstr(f,wanted)!=NULL);
    }
    fake_scan.scan_no=1234;fake_settings.ch[0].mode=CH_MODE_ALARM_ONLY;ui_render(&u,&s,f);CHECK(f[28]=='a');
    fake_protection.alarm_latch[0]=1;ui_render(&u,&s,f);CHECK(f[28]=='!');
    fake_protection.trip_seen[0]=1;ui_render(&u,&s,f);CHECK(f[28]=='#');
    fake_protection.trip_seen[0]=fake_protection.alarm_latch[0]=0;
    fake_settings.ch[0].type=CH_TYPE_OFF;ui_render(&u,&s,f);CHECK(f[28]=='-');CHECK(memcmp(f+23,"off ",4)==0);
    fake_settings.ch[0].type=CH_TYPE_K;
    fake_protection.alarm_latch[0]=fake_protection.alarm_latch[23]=1;
    u.alarm_snapshot=true;u.alarm_count=2;u.alarm_channel=1;ui_render(&u,&s,f);CHECK(memcmp(f,"ALARM  2  01 CYL3B",18)==0);
    u.screen=UI_DETAIL;u.minimum=10000;u.maximum=13720;u.cj=-5;ui_render(&u,&s,f);f[80]=0;
    CHECK(strstr(f,"1000")!=NULL && strstr(f,"1372")!=NULL);CHECK(strstr(f,"-0.5C")!=NULL);
    { uint8_t flags[]={MEAS_OPEN,MEAS_RANGE,MEAS_CM_FAIL,MEAS_SHORTED,MEAS_OVUV,MEAS_COLD,0};
      const char *labels[]={"OPEN","RANGE","CM FAIL","SHORTED","OV/UV","COLD","----"};
      for(i=0;i<7;i++) { fake_scan.meas[0].flags=flags[i];ui_render(&u,&s,f);f[80]=0;CHECK(strstr(f,labels[i])!=NULL); }
    }
    u.screen=UI_HOME;s.settings_valid=false;fake_protection.mode=CONFIG_LOCK;
    (void)fault_raise(&fake_faults,FC_G01_SETTINGS_INVALID,0);(void)fault_raise(&fake_faults,FC_G10_CALIBRATION,0);
    ui_render(&u,&s,f);CHECK(memcmp(f,"LOCKED: SETUP",12)==0);
    fake_protection.mode=SERVICE;ui_render(&u,&s,f);CHECK(memcmp(f,"SERVICE MODE",12)==0);
    fake_protection.mode=TRIPPED;fake_protection.first.valid=true;fake_protection.first.code=FC_B06_REF;
    ui_render(&u,&s,f);CHECK(memcmp(f,"TRIP B06 BANK A REF",19)==0);
    u.screen=UI_EVENTS;u.event_valid=true;u.event_count=32;u.event.power_cycles=65535;u.event.uptime_s=360000;
    ui_render(&u,&s,f);f[80]=0;CHECK(strstr(f,"65535")!=NULL);CHECK(strstr(f,"4d 04h")!=NULL);
}
static void test_difference_walk(void) {
    ui_state_t u;unsigned i;fake_reset(false);memset(&u,0,sizeof u);ui_begin(&u,&fake_settings,false);
    CHECK(!ui_find_diff(&u,&fake_settings,0));
    u.work[23].trip--;u.work[0].name[0]='X';u.address=2;u.work_pin=0x9876;
    CHECK(ui_find_diff(&u,&fake_settings,0) && u.diff==2 && u.protection_change);
    CHECK(ui_find_diff(&u,&fake_settings,1) && u.diff==165);
    CHECK(ui_find_diff(&u,&fake_settings,1) && u.diff==168);
    CHECK(ui_find_diff(&u,&fake_settings,1) && u.diff==170);
    CHECK(ui_find_diff(&u,&fake_settings,1) && u.diff==2);
    CHECK(ui_find_diff(&u,&fake_settings,-1) && u.diff==170);
    CHECK(ui_find_diff(&u,&fake_settings,-1) && u.diff==168);
    for(i=0;i<24;i++) {
        u.work[i].type=CH_TYPE_J;u.work[i].mode=CH_MODE_ALARM_ONLY;u.work[i].name[0]='X';
        u.work[i].alarm--;u.work[i].trip--;u.work[i].band++;u.work[i].limit--;
    }
    u.baud=1;CHECK(ui_find_diff(&u,&fake_settings,0) && u.diff==0);
    for(i=1;i<171;i++) CHECK(ui_find_diff(&u,&fake_settings,1) && u.diff==i);
    CHECK(ui_find_diff(&u,&fake_settings,1) && u.diff==0);
    for(i=170;i>0;i--) CHECK(ui_find_diff(&u,&fake_settings,-1) && u.diff==i);
    CHECK(ui_find_diff(&u,&fake_settings,-1) && u.diff==0);
}
static void test_editor_boundaries(void) {
    ui_state_t u;settings_t c;unsigned n;res_t r;
    fake_reset(false);memset(&u,0,sizeof u);ui_begin(&u,&fake_settings,false);u.field=UF_TYPE;
    ui_edit_begin(&u);ui_edit_key(&u,KEY_DOWN);ui_edit_key(&u,KEY_SET);
    /* 05 section 5: edits preserve the base epoch; commit derives it once. */
    CHECK(u.work[0].type==CH_TYPE_OFF && u.work[0].epoch==0 && u.work[0].band==2);
    ui_edit_begin(&u);ui_edit_key(&u,KEY_UP);ui_edit_key(&u,KEY_SET);
    CHECK((u.work[0].type&3u)==CH_TYPE_K && (u.work[0].type&0x70u)==0x70u && u.work[0].epoch==0);
    u.field=UF_ALARM;ui_edit_begin(&u);ui_edit_key(&u,KEY_SET); /* explicit zero is a valid re-entry */
    u.field=UF_TRIP;ui_edit_begin(&u);ui_edit_key(&u,KEY_UP);ui_edit_key(&u,KEY_SET);
    u.field=UF_LIMIT;ui_edit_begin(&u);ui_edit_key(&u,KEY_UP);ui_edit_key(&u,KEY_SET);
    u.entry_mask=u.position=0;r=RES_BUSY;
    for(n=0;n<64 && r==RES_BUSY;n++) r=ui_prepare(&u,&fake_settings,&c);
    CHECK(r==RES_OK && c.ch[0].type_epoch==0 && set_validate(&c)==RES_OK);
    u.work[0].epoch=63;u.field=UF_TYPE;ui_edit_begin(&u);ui_edit_key(&u,KEY_UP);ui_edit_key(&u,KEY_SET);
    CHECK(u.work[0].epoch==63 && (u.work[0].type&3u)==CH_TYPE_J);
    u.field=UF_BAND;ui_edit_begin(&u);for(n=0;n<100;n++) ui_edit_key(&u,KEY_UP);CHECK(u.edit_value==50);
    for(n=0;n<100;n++) ui_edit_key(&u,KEY_DOWN);CHECK(u.edit_value==2);
    u.field=UF_ADDRESS;ui_edit_begin(&u);for(n=0;n<300;n++) ui_edit_key(&u,KEY_UP);CHECK(u.edit_value==247);
    for(n=0;n<300;n++) ui_edit_key(&u,KEY_DOWN);CHECK(u.edit_value==1);
    fake_reset(true);fake_key(KEY_SET_LONG);pin(0);pin(0x1111);pin(0x1111);
    times(KEY_DOWN,3);fake_key(KEY_SET);CHECK(has("SAVE CHANGES?"));fake_key(KEY_SET);
    if(!has("INVALID SETTINGS")) printf("All-OFF frame: %.80s\n",fake_frame);
    CHECK(has("INVALID SETTINGS"));CHECK(fake_commits==0); /* all OFF refused */
}
static void test_pure_screens(void) {
    ui_state_t u; ui_snapshot_t s; char guarded[82]; unsigned mode,row,ch;
    fake_reset(false); memset(&u,0,sizeof u); memset(&s,0,sizeof s);
    s.settings_valid=true;s.settings=&fake_settings; s.protection=&fake_protection; s.output=&fake_output;
    s.scan=&fake_scan; s.faults=&fake_faults; s.now_ms=fake_ms;
    for(mode=0;mode<=UI_RECOVER;mode++) { u.screen=(ui_screen_t)mode;
        for(row=0;row<4;row++) { memset(guarded,'~',sizeof guarded); ui_render_row(&u,&s,(uint8_t)row,guarded+1);
            CHECK(guarded[0]=='~' && guarded[21]=='~'); }
        memset(guarded,'~',sizeof guarded); ui_render(&u,&s,guarded+1); CHECK(guarded[0]=='~' && guarded[81]=='~');
    }
    u.screen=UI_HOME;
    for(ch=0;ch<24;ch++) { unsigned page=ch/6,cell=ch%6,offset=20+(cell/2)*20+(cell%2)*10;
        u.page=(uint8_t)page; fake_scan.meas[ch].flags=MEAS_OPEN; ui_render(&u,&s,guarded+1);
        CHECK(memcmp(guarded+1+offset+3,"OPEN",4)==0); CHECK(guarded[1+offset+8]=='?'); fake_scan.meas[ch].flags=MEAS_VALID;
    }
    fake_protection.mode=START_LATCHED; ui_render(&u,&s,guarded+1); CHECK(memcmp(guarded+1,"START: ACK REQUIRED",18)==0);
    fake_protection.mode=SERVICE; memcpy(u.service_step,"P016",4); ui_render(&u,&s,guarded+1); CHECK(memcmp(guarded+1,"SERVICE MODE",12)==0);
    fake_protection.mode=RUN; (void)fault_raise(&fake_faults,FC_B12_CJ_ONE,0); ui_render(&u,&s,guarded+1); CHECK(memcmp(guarded+1,"RUN  DEGRADED CJ",16)==0);
    { uint8_t latched[(MAX_CHANNELS+7u)/8u]={1};
      u.page=0; s.trip_latched=latched; fake_protection.trip_seen[0]=0;
      ui_render(&u,&s,guarded+1); CHECK(guarded[29]=='#'); /* recovered trip remains latched */ }
}
int main(void) {
    test_navigation(); test_pin(); test_edits(); test_type_and_invalid(); test_comms_and_results();
    test_trip_and_timeout(); test_commission_recovery(); test_events(); test_pure_screens();
    test_messages_and_edges();test_display_values();test_difference_walk();
    test_editor_boundaries();
    printf("UI: %u checks, %u failures\n",checks,failures); return failures?1:0;
}
