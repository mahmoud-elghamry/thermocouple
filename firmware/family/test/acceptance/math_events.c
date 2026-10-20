#include "accept.h"
void test_math_events(void)
{
    /* Exact published points in03 section7, not copied from generated tables. */
    static const struct { ch_type_t type; int16_t temp; int32_t emf; } nist[]={
        {CH_TYPE_K,1000,4096000},{CH_TYPE_K,10000,41276000},
        {CH_TYPE_K,13720,54886000},{CH_TYPE_J,1000,5269000},
        {CH_TYPE_J,7600,42919000},{CH_TYPE_J,12000,69553000}
    };
    unsigned i; temp_dC_t t; emf_nV_t e; char input[100];
    events_t ring; event_t event,got; uint8_t bytes[16];
    for(i=0;i<sizeof(nist)/sizeof(nist[0]);++i) {
        int delta;
        (void)snprintf(input,sizeof(input),"type=%d NIST E=%ldnV T=%d(dC)",
                       (int)nist[i].type,(long)nist[i].emf,(int)nist[i].temp);
        t=TEMP_DC_INVALID;
        EQ("03-acquisition.md 7 NIST reference points",input,RES_OK,tc_inverse(nist[i].type,nist[i].emf,&t));
        delta=(int)t-nist[i].temp;
        /* 0.03C interpolation +0.05C rounding =0.08C; integer0.1C
           output at exact integer reference point can only satisfy this at equality. */
        YES("03-acquisition.md 7 <=0.03C+0.05C for T>=-50C",input,delta*10>=-8&&delta*10<=8);
        EQ("03-acquisition.md 7 CJ=0",input,RES_OK,tc_emf_to_dC(nist[i].type,nist[i].emf,0,&t));
        YES("03-acquisition.md 7 compensated reference",input,(int)t==nist[i].temp);
        EQ("03-acquisition.md 7 forward CJ",input,RES_OK,tc_dC_to_emf(nist[i].type,nist[i].temp,&e));
        /* NIST points in spec rounded to1uV; allow that0.5uV publishing precision. */
        YES("03-acquisition.md 7 forward reference",input,e>=nist[i].emf-500&&e<=nist[i].emf+500);
    }
    for(i=1;i<=2;++i) {
        ch_type_t ty=(ch_type_t)i;
        EQ("03-acquisition.md 7","forward0C",RES_OK,tc_dC_to_emf(ty,0,&e));
        EQ("03-acquisition.md 7","E(0C)=0",0,e);
        (void)tc_dC_to_emf(ty,1000,&e);
        EQ("03-acquisition.md 7 voltage-domain compensation","tip0C CJ100C negative differential EMF",
           RES_OK,tc_emf_to_dC(ty,-e,1000,&t));
        EQ("03-acquisition.md 7 negative EMF normal","tip0C CJ100C",0,t);
        (void)tc_dC_to_emf(ty,-500,&e);
        NO("03-acquisition.md 7 C08 floor","exactly-50C is permitted",tc_convert(ty,e,0,&t)&MEAS_COLD);
        (void)tc_dC_to_emf(ty,-510,&e);
        YES("03-acquisition.md 7 C08 floor","-51C is implausibly cold",tc_convert(ty,e,0,&t)&MEAS_COLD);
        YES("03-acquisition.md 7 C02","E=100mV out of table",tc_convert(ty,100000000,0,&t)&MEAS_RANGE);
        YES("03-acquisition.md 7 C02","E=-100mV out of table",tc_convert(ty,-100000000,0,&t)&MEAS_RANGE);
    }
    memset(&ring,0xff,sizeof(ring)); memset(&event,0,sizeof(event));
    event.type=EV_TRIP;event.code=FC_C10_OVER_TRIP;event.channel=1;
    event.power_cycles=0x1234;event.uptime_s=0xabcdef;
    event.value_dC=1001;event.threshold_dC=1000;
    EQ(P05 "7.1","encode16byte event",RES_OK,ev_pack(&event,bytes));
    EQ(P05 "7.1 offsets5-6","power count low byte",0x34,bytes[5]);
    EQ(P05 "7.1 offsets7-9","uptime u24 low byte",0xef,bytes[7]);
    for(i=0;i<16;++i) {
        uint8_t saved=bytes[i];bytes[i]^=1;
        YES(P05 "7.1 CRC8","corrupt one bit each byte",ev_unpack(bytes,&got)!=RES_OK);
        bytes[i]=saved;
    }
    for(i=0;i<35;++i) {
        event.sequence=(uint16_t)(65530u+i);event.value_dC=(temp_dC_t)i;
        YES(P05 "7.1 ring wrap","log35 entries across uint16 wrap",ev_log(&ring,&event)>=0);
    }
    EQ(P05 "7.1 newest modular sequence","newest after ring+sequence wrap",RES_OK,ev_get(&ring,0,&got));
    EQ(P05 "7.1 newest modular sequence","newest value",34,got.value_dC);
    {
        int newest=ev_newest(&ring);
        if(newest>=0) ring.slot[newest][15]^=1;
        EQ(P05 "7.1 bad CRC skipped","skip newest corrupted entry",RES_OK,ev_get(&ring,0,&got));
        EQ(P05 "7.1 bad CRC skipped","next-newest value",33,got.value_dC);
    }
    memset(&ring,0xff,sizeof(ring));
    for(i=0;i<3;++i) {
        event.sequence=(uint16_t)(65534u+i);event.value_dC=(temp_dC_t)i;
        (void)ev_pack(&event,ring.slot[i]);
    }
    EQ(P05 "7.1 modular sequence","raw records seq65534,65535,0 newestslot2",2,ev_newest(&ring));
}
