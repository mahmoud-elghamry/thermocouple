#ifndef HAL_BUTTONS_H
#define HAL_BUTTONS_H

#include <stdint.h>

#define HAL_BUTTON_EVENT_NONE 0x00u
#define HAL_BUTTON_EVENT_NEXT 0x01u
#define HAL_BUTTON_EVENT_UP   0x02u
#define HAL_BUTTON_EVENT_DOWN 0x04u
#define HAL_BUTTON_EVENT_SET  0x08u
#define HAL_BUTTON_EVENT_ACK  0x10u

void hal_buttons_init(void);
uint8_t hal_buttons_poll(void);

#endif
