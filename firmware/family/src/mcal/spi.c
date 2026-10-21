#include "mcal/spi.h"
#include "mcal/gpio.h"
#include <avr/io.h>
#include <util/delay.h>
#include "app/board_fast_io.h"
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
        /* Mode 3. SBI/CBI preserve PB3 even if Timer2 stops RUN mid-byte.
         * 1 us setup/high + 2 us low + 1 us high exceeds TMP126 table 7.6
         * minima. Only iso_spi owns CS and SIO_WR_N turnaround sequencing. */
        if(tx&0x80u) FAMILY_SIO_PORT|=_BV(FAMILY_MOSI_BIT);
        else FAMILY_SIO_PORT&=(uint8_t)~_BV(FAMILY_MOSI_BIT);
        tx<<=1; _delay_us(1);
        FAMILY_SIO_PORT&=(uint8_t)~_BV(FAMILY_SCK_BIT); _delay_us(2);
        rx=(uint8_t)((rx<<1)|((FAMILY_SIO_INPUT&_BV(FAMILY_MISO_BIT))?1u:0u));
        FAMILY_SIO_PORT|=_BV(FAMILY_SCK_BIT); _delay_us(1);
    }
    return rx;
}
