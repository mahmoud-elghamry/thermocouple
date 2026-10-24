#include "accept.h"
#include "app/outputs_hw.h"
static unsigned checks, failures;
void check(const char *clause, const char *input, const char *field,
           long long expected, long long actual, int line)
{
    ++checks;
    if (expected != actual) {
        ++failures;
        printf("FAIL | %s | %s | %s | expected=%lld actual=%lld | line=%d\n",
               clause, input, field, expected, actual, line);
    }
}
/* Link seam only. Hardware polarity/timers are outside the core source list. */
void outputs_hw_apply(bool pwm, bool alarm, uint16_t remaining)
{ (void)pwm; (void)alarm; (void)remaining; }
void settings_fixture(settings_t *s)
{
    unsigned i;
    memset(s,0,sizeof(*s));
    s->board_type=24; s->channel_count=24; s->address=1;
    s->baud=1; s->pin_bcd=0x1234; s->sequence=10;
    for (i=0;i<MAX_CHANNELS;++i) {
        s->ch[i].type=CH_TYPE_OFF; s->ch[i].mode=CH_MODE_TRIP;
        memset(s->ch[i].name,' ',6); s->ch[i].band_C=2;
    }
    s->ch[0].type=CH_TYPE_K; s->ch[0].alarm_dC=800;
    s->ch[0].trip_dC=1000; s->ch[0].band_C=10;
    s->ch[0].probe_limit_dC=13720;
}
void calibration_fixture(calibration_t *c, const settings_t *s)
{
    unsigned i;
    memset(c,0,sizeof(*c)); c->bank_count=3; c->sequence=20;
    for(i=0;i<MAX_CHANNELS;++i) c->baseline_nV[i]=INT32_MAX;
    c->baseline_nV[0]=4000000;
    c->tag[0]=(uint8_t)((s->ch[0].type_epoch<<2)|(unsigned)s->ch[0].type);
}
void rig_init(rig_t *r)
{
    unsigned i;
    memset(r,0,sizeof(*r)); settings_fixture(&r->cfg);
    fault_init(&r->faults); prot_init(&r->state,true,true,false);
    r->scan.scan_no=7; r->scan.settings_seq=r->cfg.sequence;
    r->scan.completed_ms=100; r->scan.scan_validated=true;
    for(i=0;i<MAX_CHANNELS;++i) {
        r->scan.meas[i].temp_dC=600; r->scan.meas[i].scan_no=7;
        r->scan.meas[i].flags=MEAS_VALID;
    }
    r->in.settings=&r->cfg; r->in.scan=&r->scan; r->in.faults=&r->faults;
    r->in.now_ms=100; r->in.settings_valid=true; r->in.calibration_valid=true;
    r->in.readback_off_ok=true; r->in.flow_ok=true;
}
void rig_step(rig_t *r) { prot_step(&r->in,&r->state,&r->out); }
void rig_ack(rig_t *r)
{
    r->in.ack_key_released=true; r->in.ack=false; rig_step(r);
    r->in.ack_key_released=false; r->in.ack=true;
    r->in.ack_age_ms=0; r->in.ack_held_ms=50; rig_step(r);
    r->in.ack=false;
}
void rig_scan(rig_t *r, uint32_t now)
{
    unsigned i;
    ++r->scan.scan_no; r->scan.settings_seq=r->cfg.sequence;
    r->scan.completed_ms=now; r->in.now_ms=now;
    for(i=0;i<MAX_CHANNELS;++i) r->scan.meas[i].scan_no=r->scan.scan_no;
    r->in.scan_complete=true; rig_step(r); r->in.scan_complete=false;
}
void rig_running(rig_t *r) { rig_init(r); rig_ack(r); rig_scan(r,101); }
int main(void)
{
    puts("Lane C independent acceptance: spec-only expectations; static fixtures; bounded loops.");
    test_channels_faults(); test_protection(); test_windows_outputs();
    test_settings(); test_storage(); test_math_events();
    printf("TOTAL checks=%u passed=%u failed=%u\n",checks,checks-failures,failures);
    return failures ? 1 : 0;
}
