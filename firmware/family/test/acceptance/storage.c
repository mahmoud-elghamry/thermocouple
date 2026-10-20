#include "accept.h"
static uint8_t ee[4096];
static void reboot_check(bool cal, unsigned active, const uint8_t *old,
                         const uint8_t *next, unsigned step)
{
    uint16_t base=cal?0x640u:0x40u, size=cal?256u:768u;
    uint32_t seq[2]={0,0}; bool valid[2]; int selected; unsigned j;
    char input[100]; settings_t s; calibration_t c;
    for(j=0;j<2;++j) {
        if(cal) {
            valid[j]=cal_unpack(ee+base+size*j,3,&c)==RES_OK;
            seq[j]=c.sequence;
        } else {
            valid[j]=set_unpack(ee+base+size*j,24,24,&s)==RES_OK;
            seq[j]=s.sequence;
        }
    }
    selected=set_select(valid[0],seq[0],valid[1],seq[1]);
    (void)snprintf(input,sizeof(input),"%s active=%u cut after operation=%u",cal?"calibration":"settings",active,step);
    YES(P05 "5 power-cut / 6 A-B",input,selected>=0);
    EQ(P05 "4 newest valid copy at every cut",input,
       valid[1u-active]&&memcmp(ee+base+size*(1u-active),next,cal?249u:402u)==0?
       (int)(1u-active):(int)active,selected);
    if(selected>=0) {
        const uint8_t *chosen=ee+base+size*(unsigned)selected;
        /* Complete records only. No mixed thresholds, no fallback to invented defaults. */
        YES(P05 "5 power-cut / 09 S07",input,
            memcmp(chosen,old,cal?249u:402u)==0 || memcmp(chosen,next,cal?249u:402u)==0);
        if(memcmp(chosen,next,cal?249u:402u)==0)
            EQ(P05 "4 modular newest / 5 power cut",input,(int)(1u-active),selected);
    }
}
static void cut_every_step(bool is_cal, unsigned active)
{
    settings_t s,n,older; calibration_t c,cn,co; set_store_t st;
    uint8_t old[768],next[768],previous[768]; unsigned step,writes=0;
    ee_op_t op; uint8_t last_value=0; bool ready=true;
    uint16_t base=is_cal?0x640u:0x40u,size=is_cal?256u:768u;
    settings_fixture(&s); n=s; older=s;
    n.sequence=11; n.ch[0].trip_dC=1100; older.sequence=9; older.ch[0].trip_dC=1200;
    calibration_fixture(&c,&s); cn=c;co=c; cn.sequence=21;cn.ref_ppm[0]=123;
    co.sequence=19;co.ref_ppm[0]=456;
    if(active==1) {
        s.sequence=UINT32_MAX; n.sequence=0; older.sequence=UINT32_MAX-1u;
        c.sequence=UINT32_MAX; cn.sequence=0; co.sequence=UINT32_MAX-1u;
    }
    memset(old,0,sizeof(old));memset(next,0,sizeof(next));memset(previous,0,sizeof(previous));
    if(is_cal) {
        (void)cal_pack(&c,old);(void)cal_pack(&cn,next);(void)cal_pack(&co,previous);
    } else {
        (void)set_pack(&s,old);(void)set_pack(&n,next);(void)set_pack(&older,previous);
    }
    memset(ee,0xff,sizeof(ee));
    memcpy(ee+base+size*active,old,size);
    memcpy(ee+base+size*(1u-active),previous,size);
    set_store_init(&st);
    EQ(P05 "5 start save","valid candidate",RES_OK,is_cal?
       cal_commit(&st,&cn,c.sequence,(uint8_t)active):set_commit(&st,&n,&s,(uint8_t)active));
    reboot_check(is_cal,active,old,next,0);
    for(step=0;step<5000;++step) {
        set_store_step(&st,ready,true,last_value,&op);
        if(op.kind==EE_WRITE || op.kind==EE_READ) {
            YES(P05 "1 map / 5 inactive slot only","operation address within inactive slot",
                op.address>=base+size*(1u-active)&&op.address<base+size*(2u-active));
            if(op.address>=sizeof(ee)) break;
            if(op.kind==EE_WRITE) { ee[op.address]=op.value;++writes; }
            last_value=ee[op.address];
        }
        reboot_check(is_cal,active,old,next,step+1);
        if(st.phase==STORE_DONE || st.phase==STORE_FAILED) break;
    }
    EQ(P05 "5 step4-5 verified switch","successful complete save",STORE_DONE,st.phase);
    EQ(P05 "5 active pointer switch","after verified readback",1u-active,st.active_slot);
    EQ(P05 "5 preserve old copy","old slot byte-for-byte",0,memcmp(ee+base+size*active,old,size));
    printf("POWER_CUT | %s active=%u | operations=%u byte_writes=%u | every operation checked\n",
           is_cal?"calibration":"settings",active,step+1,writes);
}
void test_storage(void)
{
    unsigned i,step; set_store_t st; settings_t s,n; ee_op_t op;
    for(i=0;i<4;++i) cut_every_step(i>=2,i&1u);
    for(i=0;i<2;++i) {
        settings_fixture(&s); n=s;
        if(i==0) ++n.ch[0].trip_dC; else n.ch[0].name[0]='X';
        set_store_init(&st);
        EQ(P05 "5 step1","begin protection or info save",RES_OK,set_commit(&st,&n,&s,0));
        for(step=0;step<5000;++step) {
            set_store_step(&st,true,false,0,&op);
            if(st.phase==STORE_FAILED) break;
        }
        EQ(P05 "5 step6","persistent EEPROM failure",STORE_FAILED,st.phase);
        EQ(P05 "5 step6 fault split","protection versus names",i?FC_G13_SAVE_FAIL_INFO:FC_G02_SAVE_FAIL_PROT,st.fault);
        EQ(P05 "5 step6 old active retained","failed writes",0,st.active_slot);
        EQ(P05 "5 step6 retry once","automatic retry count",1,st.retries);
    }
}
