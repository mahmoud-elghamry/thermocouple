#ifndef FAMILY_UART_H
#define FAMILY_UART_H
#include "common/types.h"
void uart_init(void);
bool uart_put(uint8_t byte);
bool uart_get(uint8_t *byte);
bool uart_tx_complete(void);
void uart_rx_isr(uint8_t byte);
void uart_tx_isr(void);
#endif
