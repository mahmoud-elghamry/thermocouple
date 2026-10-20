#ifndef FAMILY_ISO_SPI_H
#define FAMILY_ISO_SPI_H
#include "common/types.h"
#define ISO_CJ_BASE 6u
void iso_init(void);
res_t iso_select(uint8_t dev);
void iso_deselect(void);
res_t iso_xfer(uint8_t *buf, uint8_t n);
res_t iso_sio_write_enable(bool enable);
/* TMP word, command/write while drive=true, response with drive=false. */
res_t iso_word(uint16_t tx, uint16_t *rx);
uint8_t iso_owner(void);
#endif
