#include "accept.h"
/* Independent CRC oracle: bitwise long division per05 2.3, not the linked helper. */
static uint16_t crc(const uint8_t *p, unsigned n)
{
    uint16_t c=0xffff; unsigned i,b;
    for(i=0;i<n;++i) {
        c^=(uint16_t)((uint16_t)p[i]<<8);
        for(b=0;b<8;++b) c=(uint16_t)((c&0x8000u)?((uint32_t)c*2u)^0x1021u:(uint32_t)c*2u);
    }
    return c;
}
static void fix_crc(uint8_t *p,unsigned n)
{ uint16_t c=crc(p,n); p[n]=(uint8_t)c; p[n+1]=(uint8_t)(c>>8); }
static void settings_layout(const settings_t *s,uint8_t *p)
{
    unsigned i; memset(p,0,SETTINGS_SLOT_SIZE);
    p[0]=0x54; p[1]=0x53; p[2]=1; p[3]=s->board_type; p[4]=s->channel_count;
    for(i=0;i<4;++i) p[6+i]=(uint8_t)(s->sequence>>(8u*i));
    p[10]=s->address; p[11]=s->baud; p[12]=(uint8_t)s->pin_bcd; p[13]=(uint8_t)(s->pin_bcd>>8);
    for(i=0;i<s->channel_count;++i) {
        const chan_cfg_t *c=&s->ch[i]; uint8_t *b=p+16+16*i;
        b[0]=(uint8_t)c->type; b[1]=(uint8_t)c->mode; memcpy(b+2,c->name,6);
        b[8]=(uint8_t)c->alarm_dC; b[9]=(uint8_t)((uint16_t)c->alarm_dC>>8);
        b[10]=(uint8_t)c->trip_dC; b[11]=(uint8_t)((uint16_t)c->trip_dC>>8);
        b[12]=c->band_C; b[13]=c->type_epoch;
        b[14]=(uint8_t)c->probe_limit_dC; b[15]=(uint8_t)((uint16_t)c->probe_limit_dC>>8);
    }
    fix_crc(p,16u+16u*s->channel_count);
}
static void rejected_record_stays_locked(res_t status,const char *input)
{
    rig_t r; outputs_t outputs; output_decision_t decision;
    bool valid=status==RES_OK;
    NO(P05 "2.1-3 / 00-overview.md Targets reject unsupported record",input,valid);
    EQ(P05 "4 no valid copy (other slot blank)",input,-1,set_select(valid,10,false,0));
    rig_init(&r); prot_init(&r.state,valid,true,false); r.in.settings_valid=valid;
    EQ(P05 "4 / 04-protection.md 4 invalid settings boot",input,CONFIG_LOCK,r.state.mode);
    rig_ack(&r);
    EQ(P05 "4 ACK cannot clear CONFIG_LOCK",input,CONFIG_LOCK,r.state.mode);
    NO(P05 "4 RUN never granted",input,r.out.run_permission);
    NO(P05 "4 / 04-protection.md 6.1 invalid settings",input,r.out.window_refresh);
    memset(&outputs,0,sizeof(outputs));
    decision=outputs_step(&outputs,&r.out,r.in.now_ms,true,true);
    NO(P05 "4 / 04-protection.md 6.1 invalid settings PWM",input,decision.pwm_enable);
}
void test_settings(void)
{
    settings_t s,b,decoded; calibration_t cal,cal2; uint8_t p[768],q[768],cp[256];
    unsigned i,j; char input[120];
    settings_fixture(&s); settings_layout(&s,p);
    EQ(P05 "2.3 CRC16","ASCII123456789",0x29b1,set_crc16((const uint8_t *)"123456789",9));
    EQ(P05 "2.1-2.3","independently packed valid24ch",RES_OK,set_unpack(p,24,24,&decoded));
    EQ(P05 "2.1-2.3","pack fixture",RES_OK,set_pack(&s,q));
    EQ(P05 "2.1-2.3 byte layout","explicit little-endian field packing",0,memcmp(p,q,402));
    for(i=0;i<402;++i) {
        memcpy(q,p,sizeof(q)); q[i]^=1;
        (void)snprintf(input,sizeof(input),"flip bit0 at protected byte%u",i);
        YES(P05 "3 CRC whole record",input,set_unpack(q,24,24,&decoded)!=RES_OK);
    }
    /* Every validation field, with CRC recomputed to separate semantics from CRC. */
    for(i=0;i<31;++i) {
        memcpy(q,p,sizeof(q));
        switch(i) {
        case 0:q[0]=0;break; case 1:q[2]=2;break; case 2:q[3]=8;break;
        case 3:q[4]=8;break; case 4:q[5]=1;break; case 5:q[10]=0;break;
        case 6:q[10]=248;break; case 7:q[11]=2;break; case 8:q[12]=0xfa;break;
        case 9:q[14]=1;break; case 10:q[15]=1;break; case 11:q[16]=4;break;
        case 12:q[16]=3;break; case 13:q[17]=2;break; case 14:q[18]=0x1f;break;
        case 15:q[23]=0x7f;break; case 16:q[24]=0xff;q[25]=0xff;break;
        case 17:q[24]=q[26];q[25]=q[27];break;
        case 18:q[26]=0;q[27]=0;break; case 19:q[26]=0xff;q[27]=0x7f;break;
        case 20:q[28]=1;break; case 21:q[28]=51;break; case 22:q[29]=64;break;
        case 23:q[30]=0xff;q[31]=0x7f;break; case 24:q[16]=0;break;
        case 25:q[33]=1;break; /* OFF mode */
        case 26:q[40]=1;break; /* OFF alarm */
        case 27:q[42]=1;break; /* OFF trip */
        case 28:q[44]=3;break; /* OFF band */
        case 29:q[46]=1;break; /* OFF limit */
        default: q[16]=0;q[17]=0;q[24]=0;q[25]=0;q[26]=0;q[27]=0;
            q[28]=2;q[30]=0;q[31]=0;break; /* none fitted */
        }
        fix_crc(q,400);
        (void)snprintf(input,sizeof(input),"semantic mutation%u (test_accept_settings.c switch)",i);
        YES(P05 "3 / 2.1 / 2.2",input,set_unpack(q,24,24,&decoded)!=RES_OK);
    }
    /* Scalar valid endpoints, no unstated defaults. */
    b=s; b.address=247; b.baud=0; b.pin_bcd=0x9999;
    b.ch[0].alarm_dC=0; b.ch[0].trip_dC=1; b.ch[0].band_C=50;
    EQ(P05 "3 valid endpoints","address247 baud0 PIN9999 alarm0 trip0.1C band50C",RES_OK,set_validate(&b));
    b.ch[0].trip_dC=13720;
    EQ(P05 "2.2 K upper bound","trip=probe limit=1372C",RES_OK,set_validate(&b));
    b.ch[0].type=CH_TYPE_J; b.ch[0].trip_dC=12000;b.ch[0].probe_limit_dC=12000;
    EQ(P05 "2.2 J upper bound","trip=probe limit=1200C",RES_OK,set_validate(&b));
    b.ch[0].probe_limit_dC=12001;
    YES(P05 "2.2 J upper bound","probe limit1200.1C",set_validate(&b)!=RES_OK);
    EQ(P05 "4 row valid/valid","seq A10 B11",1,set_select(true,10,true,11));
    EQ(P05 "4 row valid/valid","seq A11 B10",0,set_select(true,11,true,10));
    EQ(P05 "4 modular compare","seq A0xffffffff B0",1,set_select(true,UINT32_MAX,true,0));
    EQ(P05 "4 modular compare","seq A0 B0xffffffff",0,set_select(true,0,true,UINT32_MAX));
    EQ(P05 "4 row valid/invalid","A valid B invalid",0,set_select(true,10,false,100));
    EQ(P05 "4 row invalid/valid","A invalid B valid",1,set_select(false,100,true,10));
    EQ(P05 "4 row invalid/invalid","both blank",-1,set_select(false,0,false,0));
    memset(q,0xff,sizeof(q));
    YES(P05 "4 blank EEPROM","all0xff",set_unpack(q,24,24,&decoded)!=RES_OK);
    for(i=0;i<4;++i) {
        b=s;
        if(i==0) b.ch[0].name[0]='Z';
        if(i==1) b.address=2;
        if(i==2) b.baud=0;
        if(i==3) b.pin_bcd=0x9876;
        NO(P05 "5 informational changes","names/comms/PIN",set_protection_changed(&s,&b));
    }
    for(i=0;i<6;++i) {
        b=s;
        switch(i) {
        case 0:b.ch[0].type=CH_TYPE_J;break; case 1:b.ch[0].mode=CH_MODE_ALARM_ONLY;break;
        case 2:++b.ch[0].alarm_dC;break; case 3:++b.ch[0].trip_dC;break;
        case 4:++b.ch[0].band_C;break; default:--b.ch[0].probe_limit_dC;break;
        }
        YES(P05 "5 step1 protection fields","type/mode/alarm/trip/band/probe",set_protection_changed(&s,&b));
    }
    for(i=0;i<64;++i) {
        b=s;b.ch[0].type_epoch=(uint8_t)i;
        EQ(P05 "5 type change","K->J",RES_OK,set_change_type(&b.ch[0],CH_TYPE_J));
        EQ(P05 "5 type change","clears alarm",0,b.ch[0].alarm_dC);
        EQ(P05 "5 type change","clears trip",0,b.ch[0].trip_dC);
        EQ(P05 "5 type change","clears probe limit",0,b.ch[0].probe_limit_dC);
        EQ(P05 "5 type change","epoch mod64",(i+1u)%64u,b.ch[0].type_epoch);
        YES(P05 "5 type change","cannot commit before limits reentered",set_validate(&b)!=RES_OK);
    }
    b=s; calibration_fixture(&cal,&s);
    EQ(P05 "5 type change","K->OFF",RES_OK,set_change_type(&b.ch[0],CH_TYPE_OFF));
    EQ(P05 "2.2 OFF canonical","mode",CH_MODE_TRIP,b.ch[0].mode);
    EQ(P05 "2.2 OFF canonical","band",2,b.ch[0].band_C);
    EQ(P05 "2.2 OFF canonical","alarm",0,b.ch[0].alarm_dC);
    EQ(P05 "2.2 OFF canonical","trip",0,b.ch[0].trip_dC);
    EQ(P05 "2.2 OFF canonical","limit",0,b.ch[0].probe_limit_dC);
    EQ(P05 "2.2 OFF canonical","name retained",0,memcmp(s.ch[0].name,b.ch[0].name,6));
    EQ(P05 "5 type change","OFF->K",RES_OK,set_change_type(&b.ch[0],CH_TYPE_K));
    b.ch[0].alarm_dC=800;b.ch[0].trip_dC=1000;b.ch[0].probe_limit_dC=13720;
    NO(P05 "6 / 09 S27","K->OFF->K old baseline",cal_complete(&cal,&b));
    calibration_fixture(&cal,&s);
    EQ(P05 "6 staged record","complete calibration is valid",RES_OK,cal_validate(&cal));
    YES(P05 "6 completeness","exact type+epoch and all REF",cal_complete(&cal,&s));
    for(i=0;i<256;++i) {
        cal.tag[0]=(uint8_t)i;
        EQ(P05 "6 learned-under tag","every possible tag versus K epoch0",i==1,cal_complete(&cal,&s));
    }
    for(i=0;i<64;++i) {
        unsigned ty;
        for(ty=1;ty<=2;++ty) {
            b=s;b.ch[0].type=(ch_type_t)ty;b.ch[0].type_epoch=(uint8_t)i;
            b.ch[0].probe_limit_dC=ty==1?13720:12000;
            calibration_fixture(&cal,&b);
            (void)snprintf(input,sizeof(input),"type=%u epoch=%u exact tag=%u",ty,i,cal.tag[0]);
            YES(P05 "6 type+epoch completeness",input,cal_complete(&cal,&b));
            cal.tag[0]^=1;
            NO(P05 "6 type+epoch completeness","correct epoch wrong type",cal_complete(&cal,&b));
            cal.tag[0]=(uint8_t)(((i+1u)%64u)*4u+ty);
            NO(P05 "6 type+epoch completeness","correct type wrong epoch",cal_complete(&cal,&b));
        }
    }
    calibration_fixture(&cal,&s);
    for(i=0;i<3;++i) {
        cal2=cal;cal2.ref_ppm[i]=INT32_MAX;
        EQ(P05 "6 staged use","REF marker can be serialized",RES_OK,cal_validate(&cal2));
        NO(P05 "6 completeness","missing one bank REF",cal_complete(&cal2,&s));
    }
    cal2=cal;cal2.baseline_nV[0]=INT32_MAX;
    NO(P05 "6 completeness","missing fitted channel baseline",cal_complete(&cal2,&s));
    cal2=cal;cal2.ref_ppm[0]=10001;
    YES(P05 "6 REF range","+10001ppm",cal_validate(&cal2)!=RES_OK);
    cal2.ref_ppm[0]=-10001;
    YES(P05 "6 REF range","-10001ppm",cal_validate(&cal2)!=RES_OK);
    for(i=0;i<2;++i) {
        cal2=cal;cal2.ref_ppm[0]=i?10000:-10000;
        EQ(P05 "6 REF range endpoints","+-10000ppm",RES_OK,cal_validate(&cal2));
    }
    EQ(P05 "6 calibration serialisation","pack",RES_OK,cal_pack(&cal,cp));
    EQ(P05 "6 CRC offset247","low CRC byte",crc(cp,247)&255u,cp[247]);
    for(j=0;j<249;++j) {
        uint8_t save=cp[j];cp[j]^=1;
        YES(P05 "6 CRC","single bit in each calibration byte",cal_unpack(cp,3,&cal2)!=RES_OK);
        cp[j]=save;
    }
    {
        int32_t learned[MAX_CHANNELS]; calibration_t before;
        for(i=0;i<MAX_CHANNELS;++i) learned[i]=4000000;
        before=cal; learned[0]=INT32_MAX;
        YES(P05 "6 partial learning","one fitted input carries not-learned marker",cal_learn(&cal,&s,learned)!=RES_OK);
        EQ(P05 "6 partial learning","nothing stored if one fitted fails",0,memcmp(&cal,&before,sizeof(cal)));
    }
    {
        /* 00 Targets / 05 2.1 bytes3-4, 3: only board24/count24 is this build.
           Unsupported identities are negative inputs, never larger RAM arrays. */
        static const struct { uint8_t board,channels; } wrong_build[]={
            {8,24},{40,24},{255,24},{24,8},{24,23},{24,25},{24,43},{8,8},{40,43}
        };
        for(i=0;i<sizeof(wrong_build)/sizeof(wrong_build[0]);++i) {
            b=s; b.board_type=wrong_build[i].board; b.channel_count=wrong_build[i].channels;
            (void)snprintf(input,sizeof(input),"C4 board=%u count=%u; build24/24",
                           (unsigned)b.board_type,(unsigned)b.channel_count);
            YES(P05 "2.1 bytes3-4 / 3 / 00-overview.md Targets",input,set_validate(&b)!=RES_OK);
            /* Build the rejected wire record directly in the768-byte slot.
               At most43 blocks (706 bytes with CRC); copy only the valid
               CH1 block and canonical OFF CH2 block, never index ch beyond23. */
            memset(q,0,sizeof(q)); memcpy(q,p,16);
            q[3]=b.board_type; q[4]=b.channel_count;
            for(j=0;j<b.channel_count;++j)
                memcpy(q+16u+16u*j,p+16u+(j==0?0u:16u),16);
            fix_crc(q,16u+16u*b.channel_count);
            rejected_record_stays_locked(set_unpack(q,24,24,&decoded),input);
        }
    }
    {
        /* 05 2.2 assigns raw3 to historical PT100; 00 Targets allows only
           OFF/K/J. Use the raw value without depending on a removed enum. */
        static const uint8_t unsupported_types[]={3,4,255};
        for(i=0;i<sizeof(unsupported_types)/sizeof(unsupported_types[0]);++i) {
            b=s; b.ch[0].type=(ch_type_t)unsupported_types[i];
            (void)snprintf(input,sizeof(input),"C4 CH1 raw type=%u outside OFF/K/J",
                           (unsigned)unsupported_types[i]);
            YES(P05 "2.2 type / 3 / 00-overview.md Targets",input,set_validate(&b)!=RES_OK);
            memcpy(q,p,sizeof(q)); q[16]=unsupported_types[i]; fix_crc(q,400);
            rejected_record_stays_locked(set_unpack(q,24,24,&decoded),input);
        }
    }
}
