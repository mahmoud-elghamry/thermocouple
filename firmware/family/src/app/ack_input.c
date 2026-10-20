#include "app/ack_input.h"
#include "drivers/keys.h"
#include "mcal/timer.h"
static bool held_before;
static uint32_t pressed;
void ack_input_init(void) { held_before=false; pressed=tick_ms(); keys_rearm(); }
void ack_input_cancel(void) { ack_input_init(); }
void ack_input_step(prot_in_t *in) {
    uint8_t i; bool held=(keys_held()&8u)!=0; uint32_t duration;
    if(held && !held_before) pressed=tick_ms();
    held_before=held; duration=tick_ms()-pressed;
    in->ack_key_released=!held;
    in->ack=false; in->ack_held_ms=(uint16_t)(duration>65535u?65535u:duration);
    /* The driver emits no earlier than press+50 ms and rejects queued ACKs
     * older than 500 ms. This conservative upper bound also covers a delayed
     * pass; no consumer may replay the command or consume this queue first. */
    duration=duration>=50u?duration-50u:0;
    in->ack_age_ms=(uint16_t)(duration>65535u?65535u:duration);
    for(i=0;i<7;i++) {
        key_t key=keys_get(); if(key==KEY_NONE) break;
        if(key==KEY_ACK) in->ack=true;
    }
}
