#ifndef FAMILY_FAKE_HW_H
#define FAMILY_FAKE_HW_H
#include "common/types.h"
#include "board/board_cfg.h"
void fake_reset(void);
void fake_advance(uint32_t ms);
void fake_pin(pin_t pin, bool high);
uint8_t fake_port(uint8_t port);
uint8_t fake_ddr(uint8_t port);
extern uint32_t fake_feeds, fake_bus_errors, fake_spi_bytes, fake_soft_bytes;
extern uint8_t fake_eeprom[4096];
extern char fake_uart_log[16384];
extern bool fake_uart_complete;
void fake_uart_receive(uint8_t byte,uint8_t errors);
void fake_uart_clear(void);
uint16_t fake_uart_tx_size(void);
uint8_t fake_uart_rx_count(void);
void fake_uart_step(uint32_t now_us);
extern bool fake_ref_follow;
extern uint8_t fake_fuses[3];
/* Register-level models at the MCAL seam (real drivers are linked). */
void fake_ad_reset(void);
void fake_ad_select(uint8_t bank);
uint8_t fake_ad_byte(uint8_t byte);
void fake_ad_end(void);
void fake_ad_reg(uint8_t bank, uint8_t reg, uint32_t value);
uint32_t fake_ad_get(uint8_t bank, uint8_t reg);
void fake_ad_code(uint8_t bank, uint8_t slot, uint32_t code);
void fake_ad_crc(uint8_t bank, uint8_t count);
void fake_ad_ready(uint8_t bank, uint16_t delay_ms);
void fake_ad_error(uint8_t bank, uint32_t error);
void fake_ad_por(uint8_t bank, bool enabled);
void fake_ad_channel(uint8_t bank,uint8_t slot);
void fake_ad_mclk(uint8_t bank, bool stuck, bool torn);
void fake_tmp_reset(void);
void fake_tmp_select(uint8_t sensor);
uint8_t fake_tmp_byte(uint8_t byte);
void fake_tmp_end(void);
void fake_tmp_reg(uint8_t sensor, uint8_t reg, uint16_t value);
void fake_tmp_crc(uint8_t sensor, uint8_t count);
#endif
