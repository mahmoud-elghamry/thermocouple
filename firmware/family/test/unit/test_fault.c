#include "core_test.h"
void test_fault(void)
{
    fault_registry_t r;
    unsigned code;
    fault_init(&r);
    CHECK(!fault_trip_active(&r));
    CHECK(!fault_raise(&r,FC_NONE,0) && !fault_active(&r,FC_NONE));
    for(code=1;code<FAULT_CODES;++code) {
        act_t expected;
        if(code==11 || code==12 || code==44 || code==45 || code==50 || code==51) expected=ACT_NONE;
        else if(code==13) expected=ACT_ALARM;
        else expected=ACT_TRIP; /* includes unknown code holes */
        CHECK(fault_action((fault_code_t)code,CH_MODE_TRIP)==expected);
    }
    for(code=41;code<=49;++code) {
        if(code==44 || code==45) continue;
        CHECK(fault_action((fault_code_t)code,CH_MODE_ALARM_ONLY)==ACT_ALARM);
    }
    CHECK(fault_raise(&r,FC_B02_ADC_CRC,0)); CHECK(!fault_raise(&r,FC_B02_ADC_CRC,0));
    CHECK(fault_raise(&r,FC_B02_ADC_CRC,1)); fault_clear(&r,FC_B02_ADC_CRC,0);
    CHECK(fault_active(&r,FC_B02_ADC_CRC) && fault_at(&r,FC_B02_ADC_CRC,1));
    CHECK(fault_trip_active(&r)); fault_clear(&r,FC_B02_ADC_CRC,1);
    CHECK(!fault_trip_active(&r) && fault_alarm_latched(&r));
    fault_ack(&r); CHECK(!fault_alarm_latched(&r));
    fault_raise(&r,FC_G13_SAVE_FAIL_INFO,0); CHECK(!fault_trip_active(&r));
    fault_ack(&r); CHECK(fault_alarm_latched(&r));
    fault_raise(&r,(fault_code_t)255,0); CHECK(fault_trip_active(&r));
    fault_init(&r); fault_raise(&r,FC_B01_ADC_ID,FAULT_UNITS); CHECK(fault_trip_active(&r));
    fault_init(&r); fault_raise(&r,FC_G15_FUSES,0); fault_clear(&r,FC_G15_FUSES,0);
    CHECK(fault_active(&r,FC_G15_FUSES));
    fault_init(&r); fault_raise(&r,FC_G03_FLASH_CRC,0); fault_clear(&r,FC_G03_FLASH_CRC,0);
    CHECK(fault_active(&r,FC_G03_FLASH_CRC));
    CHECK(fault_action(FC_C01_OPEN,(ch_mode_t)255)==ACT_TRIP);
}
