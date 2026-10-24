#include "accept.h"
void test_channels_faults(void)
{
    static const struct { int t; uint8_t flags; bool fresh; cond_t c; const char *row; } rows[]={
        {799,MEAS_VALID,true,COND_NORMAL,"3.1 row5 below alarm"},
        {800,MEAS_VALID,true,COND_OVER_ALARM,"3.1 row4 equal alarm"},
        {801,MEAS_VALID,true,COND_OVER_ALARM,"3.1 row4 above alarm"},
        {999,MEAS_VALID,true,COND_OVER_ALARM,"3.1 row4 below trip"},
        {1000,MEAS_VALID,true,COND_OVER_TRIP,"3.1 row3 equal trip"},
        {1001,MEAS_VALID,true,COND_OVER_TRIP,"3.1 row3 above trip"},
        {600,0,true,COND_FAULT,"3.1 row2 invalid"},
        {600,MEAS_VALID,false,COND_FAULT,"3.1 row2 stale"},
        {600,MEAS_VALID|MEAS_OPEN,true,COND_FAULT,"3.1 row2 OPEN"},
        {600,MEAS_VALID|MEAS_RANGE,true,COND_FAULT,"3.1 row2 RANGE"},
        {600,MEAS_VALID|MEAS_CM_FAIL,true,COND_FAULT,"3.1 row2 CM_FAIL"},
        {600,MEAS_VALID|MEAS_SHORTED,true,COND_FAULT,"9 C06"},
        {600,MEAS_VALID|MEAS_OVUV,true,COND_FAULT,"9 C07"},
        {-501,MEAS_VALID|MEAS_COLD,true,COND_FAULT,"9 C08"}
    };
    static const struct { fault_code_t code; act_t action; const char *name; } faults[]={
        {FC_G01_SETTINGS_INVALID,ACT_TRIP,"G01"},{FC_G02_SAVE_FAIL_PROT,ACT_TRIP,"G02"},
        {FC_G03_FLASH_CRC,ACT_TRIP,"G03 safe outputs (halt not observable)"},
        {FC_G04_INTERNAL,ACT_TRIP,"G04"},{FC_G05_SCAN_DEADLINE,ACT_TRIP,"G05"},
        {FC_G06_RUN_FEEDBACK,ACT_TRIP,"G06"},{FC_G07_ALARM_FEEDBACK,ACT_TRIP,"G07"},
        {FC_G08_ENGREF_LOST,ACT_TRIP,"G08"},{FC_G09_ENGREF_TEST,ACT_TRIP,"G09"},
        {FC_G10_CALIBRATION,ACT_TRIP,"G10"},{FC_G11_RESET_WDT,ACT_NONE,"G11"},
        {FC_G12_RESET_BOD,ACT_NONE,"G12"},{FC_G13_SAVE_FAIL_INFO,ACT_ALARM,"G13"},
        {FC_G14_ISLAND_LOST,ACT_TRIP,"G14"},{FC_G15_FUSES,ACT_TRIP,"G15"},
        {FC_B01_ADC_ID,ACT_TRIP,"B01"},{FC_B02_ADC_CRC,ACT_TRIP,"B02"},
        {FC_B03_ADC_READBACK,ACT_TRIP,"B03"},{FC_B04_ADC_ERROR,ACT_TRIP,"B04"},
        {FC_B05_ADC_STALLED,ACT_TRIP,"B05"},{FC_B06_REF,ACT_TRIP,"B06"},
        {FC_B07_AVDD,ACT_TRIP,"B07"},{FC_B08_ZERO,ACT_TRIP,"B08"},
        {FC_B09_GAIN,ACT_TRIP,"B09"},{FC_B10_CJ_BOTH,ACT_TRIP,"B10"},
        {FC_B11_CJ_DIFF,ACT_TRIP,"B11"},{FC_B12_CJ_ONE,ACT_TRIP,"B12 v1"},
        {FC_B13_SIGNATURE,ACT_TRIP,"B13"},{FC_B14_RTD,ACT_TRIP,"B14"},
        {FC_B15_ADC_RESET,ACT_TRIP,"B15"},
        {FC_C04_RATE_RESERVED,ACT_NONE,"C04 reserved"},{FC_C05_STUCK_RESERVED,ACT_NONE,"C05 reserved"}
    };
    static const fault_code_t cf[]={FC_C01_OPEN,FC_C02_RANGE,FC_C03_COMMON_MODE,
        FC_C06_SHORTED,FC_C07_OVUV,FC_C08_COLD,FC_C09_RTD};
    static const char *cn[]={"C01","C02","C03","C06","C07","C08","C09"};
    settings_t s; result_t v; unsigned i,m; rig_t r; char input[128];
    settings_fixture(&s); memset(&v,0,sizeof(v));
    for(i=0;i<sizeof(rows)/sizeof(rows[0]);++i) {
        for(m=0;m<3;++m) {
            act_t expected;
            s.ch[0].type=m==2 ? CH_TYPE_OFF : CH_TYPE_K;
            s.ch[0].mode=m==1 ? CH_MODE_ALARM_ONLY : CH_MODE_TRIP;
            v.temp_dC=(temp_dC_t)rows[i].t; v.flags=rows[i].flags;
            v.scan_no=rows[i].fresh ? 7u : 6u;
            (void)snprintf(input,sizeof(input),"%s type=%d mode=%d",rows[i].row,(int)s.ch[0].type,(int)s.ch[0].mode);
            EQ(P04 "3.1",input,m==2?COND_OFF:rows[i].c,chan_cond(&v,&s.ch[0],7));
            expected=m==2||rows[i].c==COND_NORMAL ? ACT_NONE :
                m==1||rows[i].c==COND_OVER_ALARM ? ACT_ALARM : ACT_TRIP;
            EQ(P04 "3.2",input,expected,chan_action(chan_cond(&v,&s.ch[0],7),s.ch[0].mode));
        }
    }
    settings_fixture(&s); v.flags=MEAS_VALID; v.scan_no=7;
    for(i=899;i<=901;++i) {
        v.temp_dC=(temp_dC_t)i;
        (void)snprintf(input,sizeof(input),"trip-band=900 temp=%u",i);
        EQ(P04 "3.3 trip clear",input,i<=900,chan_trip_clear(&v,&s.ch[0],7));
    }
    for(i=699;i<=701;++i) {
        v.temp_dC=(temp_dC_t)i;
        (void)snprintf(input,sizeof(input),"alarm-band=700 temp=%u",i);
        EQ(P04 "3.3 alarm clear",input,i<=700,chan_alarm_clear(&v,&s.ch[0],7));
    }
    v.flags=MEAS_OPEN;
    NO(P04 "3.3","TRIP invalid result never clear",chan_trip_clear(&v,&s.ch[0],7));
    s.ch[0].mode=CH_MODE_ALARM_ONLY;
    YES(P04 "3.3","ALARM_ONLY fault never blocks trip ACK",chan_trip_clear(&v,&s.ch[0],7));
    s.ch[0].type=(ch_type_t)99; s.ch[0].mode=CH_MODE_TRIP;
    v.flags=MEAS_VALID; v.temp_dC=600;
    EQ("01-architecture.md 5", "unknown channel type=99",COND_FAULT,chan_cond(&v,&s.ch[0],7));
    EQ("01-architecture.md 5", "unknown condition=99",ACT_TRIP,chan_action((cond_t)99,CH_MODE_TRIP));
    EQ("01-architecture.md 5", "OVER_TRIP unknown mode=99",ACT_TRIP,chan_action(COND_OVER_TRIP,(ch_mode_t)99));
    EQ("01-architecture.md 5", "NORMAL unknown mode=99",ACT_TRIP,chan_action(COND_NORMAL,(ch_mode_t)99));
    EQ("01-architecture.md 5", "OVER_ALARM unknown mode=99",ACT_TRIP,chan_action(COND_OVER_ALARM,(ch_mode_t)99));
    for(i=0;i<sizeof(faults)/sizeof(faults[0]);++i) for(m=0;m<2;++m) {
        (void)snprintf(input,sizeof(input),"row=%s mode=%u",faults[i].name,m);
        EQ(P04 "9 master table",input,faults[i].action,fault_action(faults[i].code,(ch_mode_t)m));
        rig_running(&r);
        (void)prot_on_fault(&r.state,&r.faults,faults[i].code,0,(ch_mode_t)m,0,5);
        rig_step(&r);
        EQ(P04 "9 master table integration",input,faults[i].action!=ACT_TRIP,r.out.run_permission);
        EQ(P04 "9 master table integration",input,faults[i].action!=ACT_NONE,r.out.alarm_active);
    }
    for(i=0;i<sizeof(cf)/sizeof(cf[0]);++i) for(m=0;m<3;++m) {
        rig_init(&r); r.cfg.ch[0].mode=m==1?CH_MODE_ALARM_ONLY:CH_MODE_TRIP;
        if(m==2) {
            r.cfg.ch[1]=r.cfg.ch[0]; r.cfg.ch[0].type=CH_TYPE_OFF;
            r.cfg.ch[0].alarm_dC=0; r.cfg.ch[0].trip_dC=0;
            r.cfg.ch[0].band_C=2; r.cfg.ch[0].probe_limit_dC=0;
        }
        rig_ack(&r); rig_scan(&r,101);
        if(m==2) YES(P04 "3.1 OFF baseline",cn[i],r.out.run_permission);
        (void)snprintf(input,sizeof(input),"row=%s mode=%u (2=OFF)",cn[i],m);
        (void)fault_raise(&r.faults,cf[i],0);
        rig_step(&r);
        EQ(P04 "9 TC/AC + 3.2",input,m!=0,r.out.run_permission);
        EQ(P04 "9 TC/AC + 3.2",input,m!=2,r.out.alarm_active);
    }
    EQ(P04 "9 + 00 owner rules","unknown fault=99",ACT_TRIP,fault_action((fault_code_t)99,CH_MODE_TRIP));
    rig_running(&r);
    (void)fault_raise(&r.faults,FC_B02_ADC_CRC,0);
    (void)fault_raise(&r.faults,FC_B02_ADC_CRC,1);
    fault_clear(&r.faults,FC_B02_ADC_CRC,0);
    YES("09-tests.md 3 S21","B02 bank A cleared bank B active",fault_at(&r.faults,FC_B02_ADC_CRC,1));
    rig_step(&r); EQ(P04 "9 B02", "second bank remains active",TRIPPED,r.state.mode);
}
