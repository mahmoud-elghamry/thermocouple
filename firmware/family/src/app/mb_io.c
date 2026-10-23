#include "app/modbus.h"
#include "mcal/uart.h"
#include "mcal/timer.h"
void mb_io_configure(uint8_t baud) { uart_configure_rtu(baud); }
uint32_t mb_io_now_us(void) { return timer_now_us(); }
bool mb_io_rx(mb_rx_t *out) {
    return uart_rx_sample(out);
}
bool mb_io_tx_start(const uint8_t *bytes,uint16_t length) { return uart_binary_start(bytes,length); }
bool mb_io_tx_busy(void) { return uart_binary_busy(); }
