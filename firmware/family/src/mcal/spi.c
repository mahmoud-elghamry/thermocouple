#include "mcal/spi.h"
#include "mcal/gpio.h"
#include <avr/io.h>
void spi_init(void) { SPCR=0x5D; SPSR=1; } /* OPEN-H3: 1 MHz until bus scope check */
void spi_enable(bool on) { if(on) SPCR|=_BV(SPE); else SPCR&=(uint8_t)~_BV(SPE); }
res_t spi_xfer(uint8_t tx,uint8_t *rx) {
    uint16_t i; SPDR=tx;
    for(i=0;i<1000;i++) if(SPSR&_BV(SPIF)) { *rx=SPDR; return RES_OK; }
    return RES_ERR_TIMEOUT;
}
uint8_t spi_soft_xfer(uint8_t tx) {
    uint8_t i,rx=0;
    for(i=0;i<8;i++) {
        gpio_write(PIN(PORT_B,5),(tx&0x80u)!=0); tx<<=1;
        delay_us(1); gpio_write(PIN(PORT_B,7),false); delay_us(2);
        rx=(uint8_t)((rx<<1)|(gpio_read(PIN(PORT_B,6))?1u:0u));
        gpio_write(PIN(PORT_B,7),true); delay_us(1);
    }
    return rx;
}
