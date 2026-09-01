#ifndef MCAL_SPI_H
#define MCAL_SPI_H

#include <stdint.h>

typedef enum {
    MCAL_SPI_MODE_0 = 0,
    MCAL_SPI_MODE_1 = 1,
    MCAL_SPI_MODE_2 = 2,
    MCAL_SPI_MODE_3 = 3
} mcal_spi_mode_t;

/* ATmega32 hardware SPI, master, MSB first, fCPU/16. */
void mcal_spi_master_init(mcal_spi_mode_t mode);
uint8_t mcal_spi_transfer(uint8_t value);

#endif
