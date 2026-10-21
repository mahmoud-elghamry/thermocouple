/* Target-only bounded preparation measurements; legacy images are the oracle. */
#include "services/settings.h"
#include <string.h>
extern volatile uint8_t cycle_kind,cycle_value;
extern volatile uint16_t cycle_errors;
void cycle_begin(void); void cycle_end(void);
static settings_t cfg,next;
static calibration_t cal;
static set_store_t st,reference;
void store_cycles(void) {
    uint8_t i,j,which; ee_op_t op; res_t r;
    memset(&cfg,0,sizeof cfg); memset(&cal,0,sizeof cal);
    cfg.board_type=cfg.channel_count=24; cfg.address=1; cfg.sequence=7; cal.bank_count=3;
    for(i=0;i<MAX_CHANNELS;i++) {
        for(j=0;j<6;j++) cfg.ch[i].name[j]=' ';
        cfg.ch[i].band_C=2; cal.baseline_nV[i]=CAL_MISSING;
        if(i<24) {
            cfg.ch[i].type=CH_TYPE_K; cfg.ch[i].alarm_dC=800; cfg.ch[i].trip_dC=1000;
            cfg.ch[i].probe_limit_dC=12000; cal.baseline_nV[i]=3200000; cal.tag[i]=1;
        }
    }
    for(which=0;which<3;which++) {
        next=cfg; set_store_init(&st); set_store_init(&reference);
        if(which==1) for(i=0;i<24;i++) { cfg.ch[i].type_epoch=63; cal.tag[i]=253;
            next.ch[i].type_epoch=0; next.ch[i].type=CH_TYPE_J; }
        else next.ch[0].name[0]='X';
        if(which==2) r=cal_commit(&reference,&cal,cal.sequence,0);
        else r=set_commit_with_cal(&reference,&next,&cfg,0,&cal,0);
        if(r!=RES_OK) ++cycle_errors;
        cycle_kind=33; cycle_value=which; cycle_begin();
        if(which==2) r=cal_prepare(&st,&cal,cal.sequence,0);
        else r=set_prepare_with_cal(&st,&next,&cfg,0,&cal,0);
        cycle_end(); if(r!=RES_OK) ++cycle_errors;
        for(i=0;i<200 && st.phase==STORE_PREPARE;i++) {
            cycle_kind=34; cycle_value=st.prep_stage;
            cycle_begin(); set_store_step(&st,true,true,0,&op); cycle_end();
            if(op.kind!=EE_NONE) ++cycle_errors;
        }
        if(st.phase!=STORE_INVALIDATE || memcmp(st.image,reference.image,SETTINGS_SLOT_SIZE) ||
           (which==1 && memcmp(st.wrap_cal_image,reference.wrap_cal_image,CAL_SLOT_SIZE))) ++cycle_errors;
    }
}
