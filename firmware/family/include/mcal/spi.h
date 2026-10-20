#ifndef FAMILY_SPI_H
#define FAMILY_SPI_H
#include "common/types.h"
void spi_init(void);
/* Mode 3, 1 MHz; bounded SPIF wait, never spins indefinitely. */
res_t spi_xfer(uint8_t tx, uint8_t *rx);
void spi_enable(bool enabled);
/* TMP126 bit-bang: idle high, sample after falling edge + 2 us. */
uint8_t spi_soft_xfer(uint8_t tx);
#endif
