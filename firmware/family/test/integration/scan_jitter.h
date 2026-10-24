#ifndef TEST_SCAN_JITTER_H
#define TEST_SCAN_JITTER_H
#include <stdint.h>
/* Shared, deterministic targets; actual measured pass cost may lengthen them. */
static uint8_t scan_jitter_next(uint8_t pattern,uint16_t *index,uint32_t *seed) {
    static const uint8_t cadence[3][4]={{20,8,20,20},{20,1,20,1},{19,20,3,0}};
    if(pattern<3) {
        uint8_t n=pattern==2?3:4;
        uint8_t value=cadence[pattern][*index];
        *index=(uint16_t)((*index+1u)%n); return value;
    }
    *seed^=*seed<<13; *seed^=*seed>>17; *seed^=*seed<<5;
    return (uint8_t)(1u+*seed%20u);
}
#endif
