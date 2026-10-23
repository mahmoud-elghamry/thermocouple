#ifndef PROT_FIXTURE_H
#define PROT_FIXTURE_H
#include "core_test.h"
typedef struct {
    settings_t cfg;
    scan_out_t scan;
    fault_registry_t faults;
    prot_state_t state;
    prot_in_t in;
    prot_out_t out;
} harness_t;
static inline void h_init(harness_t *h)
{
    uint8_t i;
    memset(h,0,sizeof(*h)); h->cfg=fixture_settings();
    fault_init(&h->faults); prot_init(&h->state,true,true,false);
    h->scan.scan_no=1; h->scan.settings_seq=h->cfg.sequence;
    h->scan.scan_validated=true;
    for(i=0;i<MAX_CHANNELS;++i) h->scan.meas[i]=sample(100,1);
    h->in.settings=&h->cfg; h->in.scan=&h->scan; h->in.faults=&h->faults;
    h->in.settings_valid=true; h->in.calibration_valid=true; h->in.flow_ok=true;
    h->in.readback_off_ok=true; h->in.ack_held_ms=50;
}
static inline void h_step(harness_t *h, uint32_t now, bool complete)
{
    h->in.now_ms=now; h->in.uptime_s=now/1000; h->in.scan_complete=complete;
    if(complete) {
        /* Legacy scenarios edit a whole snapshot to represent a new completion.
         * After an immediate N+1 result, publish that edited snapshot as N+2,
         * rather than falsely claiming that scan N recovered the channel.
         * Explicit results_evaluated cases preserve the supplied generations. */
        if(!h->in.results_evaluated) {
            uint8_t ch; uint32_t newest=h->scan.scan_no; bool coherent=true;
            for(ch=0;ch<h->cfg.channel_count;ch++)
                if((h->state.latest_seen[ch/8u]&(1u<<(ch%8u))) &&
                   (int32_t)(h->state.latest_scan[ch]-newest)>0) newest=h->state.latest_scan[ch];
            for(ch=0;ch<MAX_CHANNELS;ch++)
                if(h->scan.meas[ch].scan_no!=h->scan.scan_no) coherent=false;
            if(coherent && newest!=h->scan.scan_no) {
                h->scan.scan_no=newest+1u;
                for(ch=0;ch<MAX_CHANNELS;ch++) h->scan.meas[ch].scan_no=h->scan.scan_no;
            }
        }
        h->scan.completed_ms=now;
    }
    prot_step(&h->in,&h->state,&h->out);
    h->in.scan_complete=false;
}
static inline void h_ack(harness_t *h, uint32_t now)
{
    h->in.ack_key_released=true; h_step(h,now,false);
    h->in.ack_key_released=false; h->in.ack=true; h_step(h,now,false); h->in.ack=false;
}
static inline void h_run(harness_t *h)
{
    h_init(h); h_step(h,0,true); h_ack(h,1); h_step(h,2,true);
    CHECK(h->state.mode==RUN && h->out.run_permission && h->out.window_remaining_ms==APP_RUN_WINDOW_MS);
}
#endif
