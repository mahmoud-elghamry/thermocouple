#include "core_test.h"
void test_events(void)
{
    events_t ring; event_t e, out; uint8_t raw[16]; unsigned i;
    memset(&ring,0xFF,sizeof(ring)); memset(&e,0,sizeof(e));
    e.type=EV_TRIP; e.code=FC_C10_OVER_TRIP; e.channel=1; e.value_dC=-100;
    e.threshold_dC=1000; e.power_cycles=0x1234; e.uptime_s=0x12345678;
    CHECK(ev_crc8((const uint8_t *)"123456789",9)==0xF4);
    CHECK(ev_newest(&ring)==-1 && ev_get(&ring,0,&out)!=RES_OK);
    CHECK(ev_pack(&e,raw)==RES_OK && raw[5]==0x34 && raw[7]==0x78 && raw[9]==0x34);
    CHECK(ev_unpack(raw,&out)==RES_OK && out.value_dC==-100);
    for(i=EV_POWER_UP;i<=EV_PIN_RESET;++i) {
        e.type=(event_type_t)i; CHECK(ev_pack(&e,raw)==RES_OK);
        CHECK(ev_unpack(raw,&out)==RES_OK && out.type==e.type);
    }
    raw[0]^=1; CHECK(ev_unpack(raw,&out)==RES_ERR_CRC);
    for(i=0;i<70;++i) CHECK(ev_log(&ring,&e)==(int)(i%32u));
    CHECK(ev_get(&ring,0,&out)==RES_OK && out.sequence==69);
    CHECK(ev_get(&ring,31,&out)==RES_OK && out.sequence==38);
    CHECK(ev_get(&ring,32,&out)!=RES_OK);
    ring.slot[5][15]^=1; CHECK(ev_newest(&ring)==4);
    memset(&ring,0xFF,sizeof(ring)); e.sequence=UINT16_MAX;
    CHECK(ev_pack(&e,ring.slot[31])==RES_OK); CHECK(ev_log(&ring,&e)==0);
    CHECK(ev_get(&ring,0,&out)==RES_OK && out.sequence==0);
    e.type=(event_type_t)99; CHECK(ev_pack(&e,raw)!=RES_OK);
    e.type=EV_TRIP; e.channel=44; CHECK(ev_pack(&e,raw)!=RES_OK);
    e.channel=1; e.code=(fault_code_t)255; CHECK(ev_pack(&e,raw)!=RES_OK);
}
