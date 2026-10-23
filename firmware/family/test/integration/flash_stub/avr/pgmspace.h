#ifndef TEST_FLASH_PGMSPACE_H
#define TEST_FLASH_PGMSPACE_H
#include <stdint.h>
#ifdef _MSC_VER
#define __attribute__(x)
#endif
uint32_t fake_flash_address(const char *symbol);
uint8_t fake_flash_byte(uint32_t address);
uint16_t fake_flash_word(uint32_t address);
#define pgm_get_far_address(symbol) fake_flash_address(#symbol)
#define pgm_read_byte_far(address) fake_flash_byte(address)
#define pgm_read_word_far(address) fake_flash_word(address)
#endif
