#include "mcal/flash_crc.h"
#include "app/image_identity.h"
#ifdef __AVR__
#include <avr/pgmspace.h>
extern const uint8_t __data_load_end;
/* Build patches this dedicated section after linking, before HEX generation. */
const uint16_t image_crc __attribute__((section(".image_crc"),used))=0xFFFF;
#endif
static uint32_t pos;
static uint16_t crc;
static uint16_t update(uint16_t c,uint8_t b) {
    uint8_t i; c^=(uint16_t)b<<8;
    for(i=0;i<8;i++) c=(uint16_t)((c&0x8000u)?(c<<1)^0x1021u:c<<1);
    return c;
}
uint16_t flash_crc_bytes(const uint8_t *p,uint16_t n) {
    uint16_t c=0xFFFF,i; for(i=0;i<n;i++) c=update(c,p[i]); return c;
}
void flash_crc_begin(void) { pos=0; crc=0xFFFF; }
uint16_t flash_crc_value(void) { return crc; }
res_t flash_crc(void) {
#ifdef __AVR__
    uint16_t i; uint32_t end=pos<APP_IDENTITY_ADDRESS?pgm_get_far_address(__data_load_end):
        APP_IDENTITY_ADDRESS+APP_IDENTITY_BYTES;
    for(i=0;i<128 && pos<end;i++,pos++) crc=update(crc,pgm_read_byte_far(pos));
    if(pos<end) return RES_BUSY;
    /* The identity is a second programmed span; unused flash holes are not
     * code. Keep the same 128-byte bound, with one extra identity step. */
    if(pos<APP_IDENTITY_ADDRESS) { pos=APP_IDENTITY_ADDRESS; return RES_BUSY; }
    return crc==pgm_read_word_far(pgm_get_far_address(image_crc))?RES_OK:RES_ERR_CRC;
#else
    (void)pos; (void)crc; return RES_OK;
#endif
}
