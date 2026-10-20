#ifndef FAMILY_RS485_H
#define FAMILY_RS485_H
#include "common/types.h"
void rs485_init(void);
bool rs485_line(const char *line); /* <=120 chars, CRLF appended, false if busy */
void rs485_task(void); /* one byte/loop; DE released only after TXC */
bool rs485_busy(void);
#endif
