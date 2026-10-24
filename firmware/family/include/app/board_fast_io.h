#ifndef FAMILY_BOARD_FAST_IO_H
#define FAMILY_BOARD_FAST_IO_H
/* Fixed-pin MCAL fast paths, matching board_cfg_24 and 02 sections 1.1-1.3.
 * An 8-ch mapping can keep the SPI pins; their fifth key is PD5. Future mappings can supply
 * a build-selected header without changing the bit timing implementation. */
#ifdef FAMILY_FAST_IO_HEADER
#include FAMILY_FAST_IO_HEADER
#else
#define FAMILY_SIO_PORT PORTB
#define FAMILY_SIO_INPUT PINB
#define FAMILY_MOSI_BIT 5
#define FAMILY_MISO_BIT 6
#define FAMILY_SCK_BIT 7
#define FAMILY_KEY_INPUT PIND
#define FAMILY_KEY_UP_BIT 2
#define FAMILY_KEY_DOWN_BIT 3
#define FAMILY_KEY_SET_BIT 4
#define FAMILY_KEY_ACK_BIT 6
#ifndef FAMILY_CHANNELS
#define FAMILY_CHANNELS 24
#endif
#if FAMILY_CHANNELS == 24
#define FAMILY_KEY_COUNT 4
#else
#define FAMILY_KEY_COUNT 5
#define FAMILY_KEY_ESC_BIT 5
#endif
#endif
#endif
