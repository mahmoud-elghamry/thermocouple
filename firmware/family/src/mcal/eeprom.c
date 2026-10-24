#include "mcal/eeprom.h"
#include <avr/io.h>
#include <avr/interrupt.h>
bool ee_ready(void) { return (EECR&_BV(EEPE))==0; }
uint8_t ee_read(uint16_t a) {
    if(a>=4096 || !ee_ready()) return 0xFF;
    EEAR=a; EECR|=_BV(EERE); return EEDR;
}
res_t ee_write_byte(uint16_t a,uint8_t b) {
    uint8_t s;
    if(a>=4096) return RES_ERR_RANGE;
    if(!ee_ready()) return RES_BUSY;
    EEAR=a; EEDR=b; s=SREG; cli();
    EECR=_BV(EEMPE); EECR=_BV(EEPE); SREG=s; return RES_OK;
}
