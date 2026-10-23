#include "core_test.h"

static void record_rules(void)
{
    settings_t s=fixture_settings(), out, bad;
    uint8_t raw[SETTINGS_SLOT_SIZE], corrupt[SETTINGS_SLOT_SIZE];
    uint16_t i;
    CHECK(set_validate(&s)==RES_OK);
    CHECK(set_pack(&s,raw)==RES_OK);
    CHECK(raw[0]==0x54 && raw[1]==0x53 && raw[2]==1 && raw[3]==24);
    CHECK(raw[6]==7 && raw[12]==0x34 && raw[13]==0x12);
    CHECK(set_unpack(raw,24,24,&out)==RES_OK);
    CHECK(out.sequence==s.sequence && out.ch[0].trip_dC==1000);
    /* Every serialized field, including reserved header bytes and CRC. */
    for (i=0; i<402; ++i) {
        memcpy(corrupt,raw,sizeof(raw)); corrupt[i]^=0x80;
        CHECK(set_unpack(corrupt,24,24,&out)!=RES_OK);
    }
    CHECK(set_unpack(raw,8,8,&out)!=RES_OK);
#define BAD(field,value) do { bad=s; bad.field=value; CHECK(set_validate(&bad)!=RES_OK); } while(0)
    BAD(board_type,25); BAD(channel_count,23); BAD(address,0); BAD(address,248);
    BAD(baud,2); BAD(pin_bcd,0xA000); BAD(pin_bcd,0x0A00); BAD(pin_bcd,0x00A0); BAD(pin_bcd,0x000A);
    BAD(ch[0].type,(ch_type_t)99); BAD(ch[0].mode,(ch_mode_t)99);
    BAD(ch[0].name[0],0x1F); BAD(ch[0].name[5],0x7F);
    BAD(ch[0].alarm_dC,-1); BAD(ch[0].alarm_dC,1000); BAD(ch[0].trip_dC,0);
    BAD(ch[0].trip_dC,12001); BAD(ch[0].probe_limit_dC,13721);
    BAD(ch[0].band_C,1); BAD(ch[0].band_C,51); BAD(ch[0].type_epoch,64);
    BAD(ch[0].type,CH_TYPE_PT100); BAD(ch[0].type,CH_TYPE_OFF);
    BAD(ch[1].mode,CH_MODE_ALARM_ONLY); BAD(ch[1].alarm_dC,1); BAD(ch[1].trip_dC,1);
    BAD(ch[1].probe_limit_dC,1); BAD(ch[1].band_C,3);
#undef BAD
    bad=s; bad.ch[0].type=CH_TYPE_J; bad.ch[0].probe_limit_dC=12001; CHECK(set_validate(&bad)!=RES_OK);
    bad=s; CHECK(set_change_type(&bad.ch[0],CH_TYPE_OFF)==RES_OK);
    CHECK(set_validate(&bad)!=RES_OK); /* at least one fitted channel */
    bad.ch[0].type_epoch=63; CHECK(set_change_type(&bad.ch[0],CH_TYPE_J)==RES_OK);
    CHECK(bad.ch[0].type_epoch==0 && bad.ch[0].trip_dC==0 && bad.ch[0].probe_limit_dC==0);
    CHECK(set_validate(&bad)!=RES_OK); /* actual limits must be re-entered */
    bad=s; bad.board_type=40; bad.channel_count=43;
    bad.ch[40]=s.ch[0]; bad.ch[40].type=CH_TYPE_PT100; bad.ch[40].probe_limit_dC=4000;
    CHECK(set_validate(&bad)==RES_OK);
    bad.ch[40].type=CH_TYPE_K; CHECK(set_validate(&bad)!=RES_OK);
    bad=s; bad.board_type=8; bad.channel_count=8; bad.address=247; bad.baud=1; bad.pin_bcd=0x9999;
    bad.ch[0].name[0]=' '; bad.ch[0].name[5]='~'; bad.ch[0].type_epoch=63;
    bad.ch[0].band_C=50; bad.ch[0].alarm_dC=0; bad.ch[0].trip_dC=1;
    CHECK(set_pack(&bad,corrupt)==RES_OK && set_unpack(corrupt,8,8,&out)==RES_OK);
    bad=s; bad.board_type=40; bad.channel_count=43;
    CHECK(set_pack(&bad,corrupt)==RES_OK && set_unpack(corrupt,40,43,&out)==RES_OK);
    CHECK(corrupt[706]==0 && corrupt[767]==0);
    CHECK(set_crc16((const uint8_t *)"123456789",9)==0x29B1);
    CHECK(set_select(true,1,true,2)==1); CHECK(set_select(true,2,true,1)==0);
    CHECK(set_select(true,0,true,UINT32_MAX)==0); CHECK(set_select(true,UINT32_MAX,true,0)==1);
    CHECK(set_select(true,1,false,2)==0); CHECK(set_select(false,1,true,2)==1);
    CHECK(set_select(false,1,false,2)==-1); CHECK(set_select(true,1,true,1)==0);
    CHECK(set_select(true,0,true,0x80000000u)==0);
    bad=s; bad.ch[0].name[0]='X'; CHECK(!set_protection_changed(&s,&bad));
    bad.ch[0].trip_dC++; CHECK(set_protection_changed(&s,&bad));
}
static void calibration_power_cuts(void)
{
    calibration_t old=fixture_cal(), next, a, b;
    set_store_t st; ee_op_t op;
    uint8_t ee[4096], read=0, expected[CAL_SLOT_SIZE];
    unsigned step, writes=0; bool av, bv; int selected;
    old.sequence=4; old.ref_ppm[0]=CAL_MISSING; next=old; next.ref_ppm[0]=100;
    memset(ee,0xFF,sizeof(ee)); CHECK(cal_pack(&old,ee+0x640)==RES_OK);
    set_store_init(&st); CHECK(cal_commit(&st,&next,old.sequence,0)==RES_OK);
    memcpy(expected,st.image,CAL_SLOT_SIZE);
    for(step=0;step<1500 && st.phase!=STORE_DONE;++step) {
        av=cal_unpack(ee+0x640,3,&a)==RES_OK; bv=cal_unpack(ee+0x740,3,&b)==RES_OK;
        selected=set_select(av,a.sequence,bv,b.sequence); CHECK(selected>=0);
        if(selected==0) CHECK(a.sequence==4 && a.ref_ppm[0]==CAL_MISSING);
        if(selected==1) CHECK(memcmp(ee+0x740,expected,249)==0);
        set_store_step(&st,true,true,read,&op);
        if(op.kind==EE_WRITE) { ee[op.address]=op.value; ++writes; }
        if(op.kind==EE_READ) read=ee[op.address];
    }
    CHECK(st.phase==STORE_DONE && writes==250 && st.active_slot==1);
    CHECK(cal_unpack(ee+0x740,3,&b)==RES_OK && b.ref_ppm[0]==100 && b.sequence==5);
}
static void calibration_rules(void)
{
    settings_t s=fixture_settings(); calibration_t c=fixture_cal(), d;
    uint8_t raw[CAL_SLOT_SIZE], corrupt[CAL_SLOT_SIZE]; int32_t learned[MAX_CHANNELS]={0};
    uint16_t i;
    CHECK(cal_validate(&c)==RES_OK && cal_complete(&c,&s));
    CHECK(cal_pack(&c,raw)==RES_OK && cal_unpack(raw,3,&d)==RES_OK);
    CHECK(d.baseline_nV[0]==3200000 && d.tag[0]==1);
    for(i=0;i<249;++i) {
        memcpy(corrupt,raw,sizeof(raw)); corrupt[i]^=1;
        CHECK(cal_unpack(corrupt,3,&d)!=RES_OK);
    }
    raw[247]^=1; CHECK(cal_unpack(raw,3,&d)!=RES_OK);
    CHECK(cal_unpack(raw,2,&d)!=RES_OK);
    c.ref_ppm[0]=CAL_MISSING; CHECK(cal_validate(&c)==RES_OK && !cal_complete(&c,&s));
    c.ref_ppm[0]=10001; CHECK(cal_validate(&c)!=RES_OK); c.ref_ppm[0]=-10001; CHECK(cal_validate(&c)!=RES_OK);
    c=fixture_cal(); c.ref_ppm[3]=1; CHECK(cal_validate(&c)!=RES_OK);
    c=fixture_cal(); c.baseline_nV[0]=CAL_MISSING; c.tag[0]=0;
    CHECK(cal_validate(&c)==RES_OK && !cal_complete(&c,&s));
    c=fixture_cal(); c.tag[0]=2; CHECK(!cal_complete(&c,&s));
    c=fixture_cal(); s.ch[0].type_epoch=1; CHECK(!cal_complete(&c,&s));
    learned[0]=1499999; d=c; CHECK(cal_learn(&c,&s,learned)!=RES_OK && c.tag[0]==d.tag[0]);
    learned[0]=1500000; CHECK(cal_learn(&c,&s,learned)==RES_OK && cal_complete(&c,&s));
    learned[0]=10000001; CHECK(cal_learn(&c,&s,learned)!=RES_OK);
    learned[0]=10000000; CHECK(cal_learn(&c,&s,learned)==RES_OK);
    c=fixture_cal(); c.bank_count=0; CHECK(cal_validate(&c)!=RES_OK);
    c.bank_count=7; CHECK(cal_validate(&c)!=RES_OK);
    c=fixture_cal(); c.tag[0]=3; CHECK(cal_validate(&c)!=RES_OK);
    c=fixture_cal(); c.baseline_nV[0]=CAL_MISSING; CHECK(cal_validate(&c)!=RES_OK);
    c=fixture_cal(); c.baseline_nV[0]=1499999; CHECK(cal_validate(&c)!=RES_OK);
    c=fixture_cal(); c.baseline_nV[0]=10000001; CHECK(cal_validate(&c)!=RES_OK);
    c=fixture_cal(); c.ref_ppm[0]=-10000; CHECK(cal_validate(&c)==RES_OK);
    c.ref_ppm[0]=10000; CHECK(cal_validate(&c)==RES_OK);
}
static void commit_rules(void)
{
    settings_t a=fixture_settings(), b=a;
    set_store_t st; ee_op_t op; uint8_t value=0;
    uint8_t ee[4096]; unsigned steps; bool ready=true;
    memset(&st,0,sizeof(st)); memset(ee,0xFF,sizeof(ee));
    b.ch[0].trip_dC=1100;
    CHECK(set_commit(&st,&b,&a,0)==RES_OK && st.protection_change);
    for(steps=0; steps<2000 && st.phase!=STORE_DONE; ++steps) {
        set_store_step(&st,ready,true,value,&op);
        if(op.kind==EE_WRITE) ee[op.address]=op.value;
        if(op.kind==EE_READ) value=ee[op.address];
    }
    CHECK(st.phase==STORE_DONE && st.active_slot==1);
    CHECK(set_unpack(&ee[0x340],24,24,&b)==RES_OK && b.sequence==8);
    b=a; b.ch[0].name[0]='X'; CHECK(set_commit(&st,&b,&a,0)==RES_OK && !st.protection_change);
    set_store_step(&st,true,true,0,&op); CHECK(op.kind==EE_WRITE && op.value==0);
    set_store_step(&st,false,true,0,&op); CHECK(op.kind==EE_NONE); /* busy is bounded */
    for(steps=0; steps<3000 && st.phase!=STORE_FAILED; ++steps)
        set_store_step(&st,true,false,0,&op);
    CHECK(st.phase==STORE_FAILED && st.retries==1 && st.active_slot==0 && st.fault==FC_G13_SAVE_FAIL_INFO);
    b=a; b.ch[0].trip_dC=1100; CHECK(set_commit(&st,&b,&a,0)==RES_OK);
    for(steps=0; steps<3000 && st.phase!=STORE_FAILED; ++steps)
        set_store_step(&st,true,false,0,&op);
    CHECK(st.fault==FC_G02_SAVE_FAIL_PROT);
    { calibration_t c=fixture_cal(); CHECK(cal_commit(&st,&c,9,1)==RES_OK);
      CHECK(st.target_slot==0 && st.base==0x640 && st.protection_change); }
    CHECK(st.fault==FC_G02_SAVE_FAIL_PROT);
    CHECK(set_commit(&st,&b,&a,0)==RES_BUSY);
    set_store_init(&st);
    /* A corrupt read-back retries the whole write, then succeeds and clears G02. */
    b=a; b.ch[0].trip_dC=1100; CHECK(set_commit(&st,&b,&a,0)==RES_OK);
    value=0;
    for(steps=0; steps<4000 && st.phase!=STORE_DONE; ++steps) {
        set_store_step(&st,true,true,value,&op);
        if(op.kind==EE_WRITE) ee[op.address]=op.value;
        if(op.kind==EE_READ) value=(uint8_t)(ee[op.address]^(st.retries==0?1u:0u));
    }
    CHECK(st.phase==STORE_DONE && st.retries==1 && st.fault==FC_NONE);
    /* 05 section 5: candidate epoch is canonicalized against active, once. */
    set_store_init(&st);
    b=a; b.ch[0].type=CH_TYPE_J; CHECK(set_commit(&st,&b,&a,0)==RES_OK);
    CHECK(st.image[29]==1);
    set_store_init(&st); b.ch[0].type_epoch=1; CHECK(set_commit(&st,&b,&a,0)==RES_OK);
    set_store_init(&st); b=a; b.ch[0].type_epoch=1; CHECK(set_commit(&st,&b,&a,0)==RES_OK);
    CHECK(st.image[29]==0);
    b=a; CHECK(set_commit(&st,&b,&a,2)!=RES_OK);
}
static void wrap_reboot(const uint8_t ee[4096], bool off, bool multiple)
{
    settings_t sa, sb, *s; calibration_t ca, cb, *c;
    bool av, bv; int pick;
    av=set_unpack(ee+0x40,24,24,&sa)==RES_OK;
    bv=set_unpack(ee+0x340,24,24,&sb)==RES_OK;
    pick=set_select(av,sa.sequence,bv,sb.sequence); CHECK(pick>=0);
    if(pick<0) return;
    s=pick?&sb:&sa;
    av=cal_unpack(ee+0x640,3,&ca)==RES_OK;
    bv=cal_unpack(ee+0x740,3,&cb)==RES_OK;
    pick=set_select(av,ca.sequence,bv,cb.sequence); CHECK(pick>=0);
    if(pick<0) return;
    c=pick?&cb:&ca;
    CHECK(c->ref_ppm[0]==123 && c->baseline_nV[1]==4000000 && c->tag[1]==1);
    /* A second wrap, OFF -> fitted at the last board channel, is atomic with
     * the first one's baseline invalidation in the same calibration record. */
    if(multiple) {
        if(s->ch[23].type_epoch==0) {
            CHECK(s->ch[23].type==CH_TYPE_K);
            CHECK(c->baseline_nV[23]==CAL_MISSING && c->tag[23]==0);
            CHECK(!cal_complete(c,s));
        } else CHECK(s->ch[23].type_epoch==63 && s->ch[23].type==CH_TYPE_OFF);
    }
    if(s->ch[0].type_epoch==0) {
        CHECK(s->ch[0].type==(off?CH_TYPE_OFF:CH_TYPE_K));
        CHECK(c->baseline_nV[0]==CAL_MISSING && c->tag[0]==0);
        if(!off) CHECK(!cal_complete(c,s)); /* ancient K/epoch-zero baseline never resurrects */
    } else CHECK(s->ch[0].type_epoch==63 && s->ch[0].type==CH_TYPE_J);
}
static void epoch_wrap_power_cuts(void)
{
    unsigned settings_slot, cal_slot, off;
    for(settings_slot=0;settings_slot<2;++settings_slot)
    for(cal_slot=0;cal_slot<2;++cal_slot)
    for(off=0;off<2;++off) {
        settings_t old=fixture_settings(), next, stale;
        calibration_t cal=fixture_cal(), stale_cal;
        set_store_t st; ee_op_t op;
        uint8_t ee[4096], read=0; unsigned step, cal_reads=0;
        old.ch[1]=old.ch[0];
        old.sequence=UINT32_MAX; old.ch[0].type=CH_TYPE_J; old.ch[0].type_epoch=63;
        old.ch[23].type_epoch=63;
        next=old; CHECK(set_change_type(&next.ch[0],off?CH_TYPE_OFF:CH_TYPE_K)==RES_OK);
        if(!off) { next.ch[0].alarm_dC=800; next.ch[0].trip_dC=1000; next.ch[0].probe_limit_dC=12000; }
        CHECK(set_change_type(&next.ch[23],CH_TYPE_K)==RES_OK);
        next.ch[23].alarm_dC=800; next.ch[23].trip_dC=1000; next.ch[23].probe_limit_dC=12000;
        cal.sequence=UINT32_MAX; cal.ref_ppm[0]=123;
        cal.baseline_nV[1]=4000000; cal.tag[1]=1;
        cal.baseline_nV[23]=3500000; cal.tag[23]=1;
        /* K/epoch-zero tag left from 64 changes ago, including in the stale slot. */
        stale=old; --stale.sequence; stale_cal=cal; --stale_cal.sequence;
        memset(ee,0xFF,sizeof(ee));
        CHECK(set_pack(&old,ee+0x40+768*settings_slot)==RES_OK);
        CHECK(set_pack(&stale,ee+0x40+768*(1-settings_slot))==RES_OK);
        CHECK(cal_pack(&cal,ee+0x640+256*cal_slot)==RES_OK);
        CHECK(cal_pack(&stale_cal,ee+0x640+256*(1-cal_slot))==RES_OK);
        set_store_init(&st);
        CHECK(set_commit(&st,&next,&old,(uint8_t)settings_slot)==RES_ERR_RANGE);
        CHECK(set_commit_with_cal(&st,&next,&old,(uint8_t)settings_slot,NULL,(uint8_t)cal_slot)==RES_ERR_RANGE);
        CHECK(set_commit_with_cal(&st,&next,&old,(uint8_t)settings_slot,&cal,2)==RES_ERR_RANGE);
        stale_cal=cal; stale_cal.bank_count=1;
        CHECK(set_commit_with_cal(&st,&next,&old,(uint8_t)settings_slot,&stale_cal,(uint8_t)cal_slot)==RES_ERR_RANGE);
        stale_cal=cal; stale_cal.tag[23]=0;
        CHECK(set_commit_with_cal(&st,&next,&old,(uint8_t)settings_slot,&stale_cal,(uint8_t)cal_slot)==RES_ERR_RANGE);
        CHECK(st.phase==STORE_IDLE); /* validation failures emit no EEPROM work */
        CHECK(set_commit_with_cal(&st,&next,&old,(uint8_t)settings_slot,&cal,(uint8_t)cal_slot)==RES_OK);
        for(step=0;step<2000 && st.phase!=STORE_DONE && st.phase!=STORE_FAILED;++step) {
            wrap_reboot(ee,off!=0,true);
            set_store_step(&st,true,true,read,&op);
            if(op.kind==EE_WRITE) {
                if(op.address<0x640) CHECK(cal_reads==249);
                ee[op.address]=op.value;
            }
            if(op.kind==EE_READ) { read=ee[op.address]; if(op.address>=0x640) ++cal_reads; }
        }
        CHECK(st.phase==STORE_DONE && st.active_slot==1-settings_slot && st.calibration_active_slot==1-cal_slot);
        wrap_reboot(ee,off!=0,true);
    }
}
static void wrap_failure_paths(void)
{
    unsigned stage, failure_kind;
    for(stage=0;stage<2;++stage) for(failure_kind=0;failure_kind<3;++failure_kind) {
        settings_t old=fixture_settings(), next;
        calibration_t cal=fixture_cal(), current_cal;
        set_store_t st; ee_op_t op;
        uint8_t ee[4096], read=0, current_slot;
        bool success=true, injected=false; unsigned steps, pass;
        old.ch[1]=old.ch[0]; old.ch[0].type=CH_TYPE_J; old.ch[0].type_epoch=63;
        next=old; next.ch[0].type=CH_TYPE_K; next.ch[0].type_epoch=0;
        cal.ref_ppm[0]=123; cal.baseline_nV[1]=4000000; cal.tag[1]=1;
        memset(ee,0xFF,sizeof(ee));
        CHECK(set_pack(&old,ee+0x40)==RES_OK && cal_pack(&cal,ee+0x640)==RES_OK);
        set_store_init(&st);
        CHECK(set_commit_with_cal(&st,&next,&old,0,&cal,0)==RES_OK && st.protection_change);
        CHECK(set_commit_with_cal(&st,&next,&old,0,&cal,0)==RES_BUSY);
        for(pass=0;pass<2;++pass) {
            for(steps=0;steps<4000 && st.phase!=STORE_DONE && st.phase!=STORE_FAILED;++steps) {
                set_store_step(&st,true,success,read,&op); success=true;
                if(op.kind==EE_WRITE) {
                    if(pass==0 && failure_kind==0 && ((op.address<0x640)==(stage!=0))) {
                        success=false; injected=true;
                    } else ee[op.address]=op.value;
                }
                if(op.kind==EE_READ) {
                    read=ee[op.address];
                    if(pass==0 && failure_kind!=0 && ((op.address<0x640)==(stage!=0)) &&
                       (failure_kind==1 || !injected)) { read^=1; injected=true; }
                }
                wrap_reboot(ee,false,false);
                if(pass==1 && st.phase!=STORE_DONE) CHECK(st.fault==FC_G02_SAVE_FAIL_PROT);
            }
            CHECK(injected);
            if(failure_kind==2 || pass==1) {
                CHECK(st.phase==STORE_DONE && st.fault==FC_NONE && st.active_slot==1);
                break;
            }
            CHECK(st.phase==STORE_FAILED && st.fault==FC_G02_SAVE_FAIL_PROT && st.active_slot==0);
            current_slot=st.calibration_active_slot;
            CHECK(current_slot==(stage?1:0));
            /* 05 section 5: epoch wrap must persist baseline invalidation across
             * power cuts. After calibration verifies, neither retry API may use
             * the stale slot or alter the failed transaction when rejecting it. */
            if(stage) {
                set_store_t probe=st;
                CHECK(set_commit_with_cal(&st,&next,&old,0,&cal,0)==RES_ERR_RANGE);
                CHECK(memcmp(&st,&probe,sizeof(st))==0);
                CHECK(cal_commit(&probe,&cal,cal.sequence,0)==RES_ERR_RANGE);
                CHECK(memcmp(&st,&probe,sizeof(st))==0);
            }
            CHECK(cal_unpack(ee+0x640+256*current_slot,3,&current_cal)==RES_OK);
            CHECK(set_commit_with_cal(&st,&next,&old,0,&current_cal,current_slot)==RES_OK);
            read=0; success=true;
        }
        wrap_reboot(ee,false,false);
    }
}
void test_settings(void)
{
    record_rules(); calibration_rules(); calibration_power_cuts(); commit_rules();
    epoch_wrap_power_cuts(); wrap_failure_paths();
}
