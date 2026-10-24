#ifndef ACCEPT_H
#define ACCEPT_H
#include <stdio.h>
#include <string.h>
#include "app/protection.h"
#include "app/outputs.h"
#include "services/tc_math.h"
#include "services/events.h"
/* Expectations originate in firmware/spec, never in production source/tests. */
void check(const char *clause, const char *input, const char *field,
           long long expected, long long actual, int line);
#define EQ(c,i,e,a) check(c,i,#a,(long long)(e),(long long)(a),__LINE__)
#define YES(c,i,a) EQ(c,i,1,!!(a))
#define NO(c,i,a) EQ(c,i,0,!!(a))
#define P04 "04-protection.md "
#define P05 "05-settings-events.md "
typedef struct {
    settings_t cfg;
    scan_out_t scan;
    fault_registry_t faults;
    prot_state_t state;
    prot_in_t in;
    prot_out_t out;
} rig_t;
void settings_fixture(settings_t *s);
void calibration_fixture(calibration_t *c, const settings_t *s);
void rig_init(rig_t *r);
void rig_step(rig_t *r);
void rig_ack(rig_t *r);
void rig_running(rig_t *r);
void rig_scan(rig_t *r, uint32_t now);
void test_channels_faults(void);
void test_protection(void);
void test_windows_outputs(void);
void test_settings(void);
void test_storage(void);
void test_math_events(void);
#endif
