#include "services/settings.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks; if(!(x)) { printf("prepare FAIL %d: %s\n",__LINE__,#x); exit(1); } } while(0)
static settings_t cfg,next;
static calibration_t cal;
static set_store_t reference,st;
static void prepare(void) {
    ee_op_t op; unsigned n;
    for(n=0;n<200 && st.phase==STORE_PREPARE;n++) {
        set_store_step(&st,true,true,0,&op); CHECK(op.kind==EE_NONE);
    }
    CHECK(n>1 && n<200 && st.phase==STORE_INVALIDATE);
    CHECK(memcmp(st.image,reference.image,SETTINGS_SLOT_SIZE)==0);
    if(st.settings_after_cal) CHECK(memcmp(st.wrap_cal_image,reference.wrap_cal_image,CAL_SLOT_SIZE)==0);
    CHECK(st.protection_change==reference.protection_change && st.settings_after_cal==reference.settings_after_cal);
    CHECK(st.base==reference.base && st.length==reference.length);
}
int main(void) {
    unsigned i; ee_op_t op;
    memset(&cfg,0,sizeof cfg); memset(&cal,0,sizeof cal);
    cfg.board_type=cfg.channel_count=24; cfg.address=1; cfg.sequence=7; cal.bank_count=3;
    for(i=0;i<MAX_CHANNELS;i++) { memset(cfg.ch[i].name,' ',6); cfg.ch[i].band_C=2; cal.baseline_nV[i]=CAL_MISSING; }
    cfg.ch[0].type=CH_TYPE_K; cfg.ch[0].alarm_dC=800; cfg.ch[0].trip_dC=1000; cfg.ch[0].probe_limit_dC=12000;
    cal.baseline_nV[0]=3200000; cal.tag[0]=1;
    for(i=0;i<3;i++) {
        next=cfg;
        if(i==0) next.ch[0].name[0]='X';
        if(i==1) next.ch[0].trip_dC=1100;
        if(i==2) { cfg.ch[0].type_epoch=63; cal.tag[0]=253; next=cfg; next.ch[0].type=CH_TYPE_J; next.ch[0].type_epoch=0; }
        set_store_init(&reference); set_store_init(&st);
        CHECK(set_commit_with_cal(&reference,&next,&cfg,0,&cal,0)==RES_OK);
        CHECK(set_prepare_with_cal(&st,&next,&cfg,0,&cal,0)==RES_OK && st.phase==STORE_PREPARE);
        CHECK(st.protection_change==(i!=0)); prepare();
    }
    set_store_init(&reference); set_store_init(&st);
    CHECK(cal_commit(&reference,&cal,cal.sequence,0)==RES_OK);
    CHECK(cal_prepare(&st,&cal,cal.sequence,0)==RES_OK); prepare();
    set_store_init(&st); next=cfg; next.ch[0].name[0]=0;
    CHECK(set_prepare_with_cal(&st,&next,&cfg,0,&cal,0)==RES_OK);
    for(i=0;i<200 && st.phase==STORE_PREPARE;i++) {
        set_store_step(&st,true,true,0,&op); CHECK(op.kind==EE_NONE);
    }
    CHECK(st.phase==STORE_FAILED);
    /* 05 section 5 (2026-10-23): derive epochs once from the ACTIVE record,
     * independent of repeated editor changes or candidate epoch values. */
    cfg.ch[0].type_epoch=5;
    for(i=0;i<2;i++) {
        settings_t loaded;
        next=cfg; next.ch[0].type_epoch=17;
        if(i) next.ch[0].type=CH_TYPE_J;
        set_store_init(&reference); set_store_init(&st);
        CHECK(set_commit_with_cal(&reference,&next,&cfg,0,&cal,0)==RES_OK);
        CHECK(set_prepare_with_cal(&st,&next,&cfg,0,&cal,0)==RES_OK); prepare();
        CHECK(set_unpack(st.image,24,24,&loaded)==RES_OK);
        CHECK(loaded.ch[0].type_epoch==(i?6:5));
    }
    printf("Store preparation: %u checks PASS\n",checks); return 0;
}
