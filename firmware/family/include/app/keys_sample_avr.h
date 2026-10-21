#ifndef FAMILY_KEYS_SAMPLE_AVR_H
#define FAMILY_KEYS_SAMPLE_AVR_H
#include <avr/io.h>
#include "app/board_fast_io.h"
/* Driver-owned debounce state; only the 1 ms ISR writes it after init. */
extern volatile uint8_t keys_history[5],keys_stable;
static inline void keys_sample_fast(void) {
    uint8_t pins=FAMILY_KEY_INPUT,h;
#define SAMPLE(i,b) do { \
    h=(uint8_t)((keys_history[i]<<1)|((pins>>b)&1u)); keys_history[i]=h; \
    if(h==0) keys_stable|=(uint8_t)(1u<<i); \
    else if(h==255) keys_stable&=(uint8_t)~(1u<<i); \
} while(0)
    SAMPLE(0,FAMILY_KEY_UP_BIT); SAMPLE(1,FAMILY_KEY_DOWN_BIT);
    SAMPLE(2,FAMILY_KEY_SET_BIT); SAMPLE(3,FAMILY_KEY_ACK_BIT);
#if FAMILY_KEY_COUNT == 5
    SAMPLE(4,FAMILY_KEY_ESC_BIT);
#endif
#undef SAMPLE
}
#endif
