#include "drivers/iso_spi.h"
#include "board/board_cfg.h"
#include "mcal/gpio.h"
#include "mcal/spi.h"
static uint8_t owner=0xFF;
void iso_init(void) { owner=0xFF; gpio_write(board()->sio_wr_n,true); spi_init(); }
uint8_t iso_owner(void) { return owner; }
res_t iso_select(uint8_t d) {
    if(owner!=0xFF) return RES_BUSY;
    if(!((d<board()->banks) || (d>=ISO_CJ_BASE && d<ISO_CJ_BASE+board()->cj_count))) return RES_ERR_RANGE;
    gpio_write(board()->sio_wr_n,true); gpio_write(PIN(PORT_B,7),true);
    if(d>=ISO_CJ_BASE) spi_enable(false);
    owner=d; gpio_write(d<ISO_CJ_BASE?board()->adc_cs[d]:board()->cj_cs[d-ISO_CJ_BASE],false);
    delay_us(1); return RES_OK;
}
void iso_deselect(void) {
    if(owner==0xFF) return;
    delay_us(1); gpio_write(board()->sio_wr_n,true); delay_us(1);
    gpio_write(owner<ISO_CJ_BASE?board()->adc_cs[owner]:board()->cj_cs[owner-ISO_CJ_BASE],true);
    delay_us(1); owner=0xFF; spi_enable(true);
}
res_t iso_sio_write_enable(bool en) {
    if(en && (owner<ISO_CJ_BASE || owner==0xFF)) return RES_ERR_RANGE;
    gpio_write(board()->sio_wr_n,!en); delay_us(1); return RES_OK;
}
res_t iso_xfer(uint8_t *p,uint8_t n) {
    uint8_t i; res_t r;
    if(owner>=ISO_CJ_BASE) return RES_ERR_RANGE;
    for(i=0;i<n;i++) { r=spi_xfer(p[i],&p[i]); if(r!=RES_OK) return r; }
    return RES_OK;
}
res_t iso_word(uint16_t tx,uint16_t *rx) {
    uint8_t h,l;
    if(owner<ISO_CJ_BASE || owner==0xFF) return RES_ERR_RANGE;
    h=spi_soft_xfer((uint8_t)(tx>>8)); l=spi_soft_xfer((uint8_t)tx);
    *rx=(uint16_t)(((uint16_t)h<<8)|l); return RES_OK;
}
