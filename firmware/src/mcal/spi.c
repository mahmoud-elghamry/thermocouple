#include "mcal/spi.h"

#include <avr/io.h>
#include <stddef.h>
#include <stdint.h>

#define MCAL_SPI_TIMEOUT_LOOPS UINT16_MAX

void mcal_spi_master_init(mcal_spi_mode_t mode)
{
    uint8_t control = (uint8_t)((1u << SPE) | (1u << MSTR) | (1u << SPR0));

    /* Hardware SPI pins: PB5 MOSI, PB6 MISO, PB7 SCK.  PB4 must remain an
       output so the AVR cannot accidentally fall back to slave mode. */
    DDRB |= (uint8_t)((1u << PB4) | (1u << PB5) | (1u << PB7));
    DDRB &= (uint8_t)~(1u << PB6);

    /* MISO pull-up.  Eight converters share the line and every one of them
       releases it while its CS is high, so between transactions the input
       would otherwise float and toggle on noise (I-017). */
    PORTB |= (uint8_t)(1u << PB6);

    if (mode == MCAL_SPI_MODE_1 || mode == MCAL_SPI_MODE_3) {
        control |= (uint8_t)(1u << CPHA);
    }
    if (mode == MCAL_SPI_MODE_2 || mode == MCAL_SPI_MODE_3) {
        control |= (uint8_t)(1u << CPOL);
    }

    SPCR = control;
    SPSR = 0u;
}

bool mcal_spi_transfer(uint8_t value, uint8_t *received)
{
    uint16_t timeout = MCAL_SPI_TIMEOUT_LOOPS;
    uint8_t discard;

    if (received == NULL) {
        return false;
    }

    SPDR = value;
    while ((SPSR & (uint8_t)(1u << SPIF)) == 0u) {
        if (timeout == 0u) {
            /* SPIF clears by reading SPSR and then SPDR.  Returning without
               the SPDR read leaves the flag set, so the next transfer sees a
               stale completion and the byte stream slips by one - permanently,
               and with no symptom other than wrong temperatures (I-014).
               SPSR has already been read by the loop condition. */
            discard = SPDR;
            (void)discard;
            return false;
        }
        --timeout;
    }
    *received = SPDR;
    return true;
}
