#include "app/ack_input.h"
#include "drivers/keys.h"
#include "mcal/timer.h"
void ack_input_init(void) { keys_rearm(); }
void ack_input_cancel(void) { ack_input_init(); }
void ack_input_step(prot_in_t *in) {
    uint8_t i; key_event_t e;
    in->ack_key_released=(keys_held()&8u)==0;
    in->ack=false; in->ack_held_ms=in->ack_age_ms=0;
    for(i=0;i<7;i++) {
        if(!keys_get_event(&e)) break;
        if(e.key==KEY_ACK) {
            uint32_t held=e.event_ms-e.pressed_ms,age=tick_ms()-e.event_ms;
            in->ack=true; in->ack_held_ms=(uint16_t)(held>65535u?65535u:held);
            in->ack_age_ms=(uint16_t)(age>65535u?65535u:age);
        }
    }
}
