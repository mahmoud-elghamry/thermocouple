#include "core_test.h"
void test_channel(void)
{
    settings_t s=fixture_settings(); result_t r=sample(799,4); chan_cfg_t *c=&s.ch[0];
    const cond_t conditions[]={COND_FAULT,COND_OVER_TRIP,COND_OVER_ALARM,COND_NORMAL,COND_OFF};
    const act_t trip[]={ACT_TRIP,ACT_TRIP,ACT_ALARM,ACT_NONE,ACT_NONE};
    const act_t alarm[]={ACT_ALARM,ACT_ALARM,ACT_ALARM,ACT_NONE,ACT_NONE};
    const uint8_t flags[]={MEAS_OPEN,MEAS_RANGE,MEAS_CM_FAIL,MEAS_SHORTED,MEAS_OVUV,MEAS_COLD};
    const fault_code_t codes[]={FC_C01_OPEN,FC_C02_RANGE,FC_C03_COMMON_MODE,FC_C06_SHORTED,FC_C07_OVUV,FC_C08_COLD};
    unsigned i;
    CHECK(chan_cond(&r,c,4)==COND_NORMAL);
    r.temp_dC=800; CHECK(chan_cond(&r,c,4)==COND_OVER_ALARM);
    r.temp_dC=999; CHECK(chan_cond(&r,c,4)==COND_OVER_ALARM);
    r.temp_dC=1000; CHECK(chan_cond(&r,c,4)==COND_OVER_TRIP);
    r.temp_dC=1001; CHECK(chan_cond(&r,c,4)==COND_OVER_TRIP);
    r.temp_dC=12001; CHECK(chan_cond(&r,c,4)==COND_FAULT);
    CHECK(chan_cause(&r,chan_cond(&r,c,4))==FC_C02_RANGE);
    CHECK(chan_cond(&r,c,5)==COND_FAULT);
    for(i=0;i<sizeof(flags);++i) {
        r.flags=(uint8_t)(MEAS_VALID|flags[i]); CHECK(chan_cond(&r,c,4)==COND_FAULT);
        CHECK(chan_cause(&r,COND_FAULT)==codes[i]);
    }
    r.flags=0; CHECK(chan_cond(&r,c,4)==COND_FAULT);
    for(i=0;i<5;++i) {
        CHECK(chan_action(conditions[i],CH_MODE_TRIP)==trip[i]);
        CHECK(chan_action(conditions[i],CH_MODE_ALARM_ONLY)==alarm[i]);
    }
    CHECK(chan_action((cond_t)99,CH_MODE_ALARM_ONLY)==ACT_TRIP);
    CHECK(chan_action(COND_NORMAL,(ch_mode_t)99)==ACT_TRIP);
    r=sample(980,4); CHECK(chan_trip_clear(&r,c,4));
    r.temp_dC=981; CHECK(!chan_trip_clear(&r,c,4));
    r.temp_dC=780; CHECK(chan_alarm_clear(&r,c,4));
    r.temp_dC=781; CHECK(!chan_alarm_clear(&r,c,4));
    c->mode=CH_MODE_ALARM_ONLY; r.flags=MEAS_OPEN; CHECK(chan_trip_clear(&r,c,4));
    c->type=CH_TYPE_OFF; CHECK(chan_cond(&r,c,4)==COND_OFF && chan_alarm_clear(&r,c,4));
    c->type=(ch_type_t)99; CHECK(chan_cond(&r,c,4)==COND_FAULT);
    c->type=CH_TYPE_K; c->mode=(ch_mode_t)99; CHECK(chan_cond(&r,c,4)==COND_FAULT);
}
