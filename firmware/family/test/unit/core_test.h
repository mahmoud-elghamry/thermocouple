#include "app/timing.h"
#ifndef CORE_TEST_H
#define CORE_TEST_H
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "app/outputs.h"
#include "services/events.h"
#include "services/tc_math.h"
extern unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
    printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #x); } } while (0)
static inline settings_t fixture_settings(void)
{
    settings_t s;
    uint8_t i;
    memset(&s, 0, sizeof(s));
    s.board_type=24; s.channel_count=24; s.address=1; s.pin_bcd=0x1234;
    s.sequence=7;
    for (i=0; i<MAX_CHANNELS; ++i) {
        memcpy(s.ch[i].name,"      ",6); s.ch[i].band_C=2;
    }
    s.ch[0].type=CH_TYPE_K; s.ch[0].alarm_dC=800; s.ch[0].trip_dC=1000;
    s.ch[0].probe_limit_dC=12000;
    return s;
}
static inline calibration_t fixture_cal(void)
{
    calibration_t c;
    uint8_t i;
    memset(&c,0,sizeof(c)); c.bank_count=3;
    for(i=0; i<MAX_CHANNELS; ++i) c.baseline_nV[i]=CAL_MISSING;
    c.baseline_nV[0]=3200000; c.tag[0]=CH_TYPE_K;
    return c;
}
static inline result_t sample(temp_dC_t t, uint32_t n)
{
    result_t r; memset(&r,0,sizeof(r)); r.temp_dC=t; r.scan_no=n; r.flags=MEAS_VALID; return r;
}
void test_settings(void); void test_events(void); void test_fault(void);
void test_channel(void); void test_protection(void); void test_outputs(void);
void test_tc_math(void); void test_scenarios(void);
#endif
