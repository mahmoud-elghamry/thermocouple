#ifndef FAMILY_BOARD_CFG_H
#define FAMILY_BOARD_CFG_H
#include "common/types.h"
/* Encoded port A..D in bits 4:3, bit number in bits 2:0. */
typedef uint8_t pin_t;
#define PIN(p,b) ((pin_t)((p)*8u+(b)))
enum { PORT_A, PORT_B, PORT_C, PORT_D };
typedef struct { uint8_t bank, ain_p, ain_m; uint16_t cj_weight_q8; } channel_hw_t;
typedef struct {
    uint8_t channels, banks, cj_count;
    pin_t adc_cs[MAX_BANKS], cj_cs[2u*MAX_BANKS], sio_wr_n, refok, reftest;
    pin_t run, run_sense, alarm, alarm_sense, de;
    pin_t keys[5]; uint8_t key_count;
    channel_hw_t channel[MAX_CHANNELS];
    uint8_t port_init[4],ddr_init[4];
} board_t;
/* Immutable hardware mapping, no settings or temperatures. */
const board_t *board(void);
#endif
