#include "board/board_cfg.h"
#define CH(b,k,w) {b,2u*(k),2u*(k)+1u,w}
#define BANK(b) CH(b,0,0),CH(b,1,0),CH(b,2,32),CH(b,3,96),CH(b,4,160),CH(b,5,224),CH(b,6,256),CH(b,7,256)
static const board_t cfg = {
    24,3,6,CS_DIRECT,
    {PIN(PORT_B,4),PIN(PORT_B,0),PIN(PORT_B,1),0,0,0},
    {PIN(PORT_B,2),PIN(PORT_C,0),PIN(PORT_C,1),PIN(PORT_C,3),PIN(PORT_C,4),PIN(PORT_C,5),0,0,0,0},
    PIN(PORT_D,5),PIN(PORT_A,2),PIN(PORT_A,3),
    PIN(PORT_B,3),PIN(PORT_C,2),PIN(PORT_C,6),PIN(PORT_C,7),PIN(PORT_D,7),
    {PIN(PORT_D,2),PIN(PORT_D,3),PIN(PORT_D,4),PIN(PORT_D,6),0},4,false,
    {BANK(0),BANK(1),BANK(2)}, /* OPEN-Q14: provisional clamped header weights */
    {0,0x97,0x3B,0x74},{0xFB,0xBF,0x7B,0xA2}
};
const board_t *board(void) { return &cfg; }
