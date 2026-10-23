#ifndef FAMILY_UART_H
#define FAMILY_UART_H
#include "common/types.h"
void uart_init(void);
bool uart_put(uint8_t byte);
bool uart_get(uint8_t *byte);
bool uart_tx_complete(void);
void uart_rx_isr(uint8_t byte);
void uart_tx_isr(void);
typedef struct { uint32_t at_us; uint8_t byte,flags; } uart_sample_t;
void uart_configure_rtu(uint8_t baud);
bool uart_rx_sample(uart_sample_t *sample);
bool uart_binary_start(const uint8_t *bytes,uint16_t length);
bool uart_binary_busy(void);
void uart_rx_error_isr(uint8_t byte,uint8_t errors);
void uart_complete_isr(void);
#endif
