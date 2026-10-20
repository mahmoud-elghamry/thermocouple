#ifndef FAMILY_KEYS_H
#define FAMILY_KEYS_H
#include "common/types.h"
typedef enum { KEY_NONE, KEY_UP, KEY_DOWN, KEY_SET, KEY_ACK, KEY_ESC, KEY_SET_LONG } key_t;
void keys_init(void);
void keys_sample_isr(void);
void keys_task(void);
key_t keys_get(void);
void keys_rearm(void);
uint8_t keys_held(void); /* bits UP DOWN SET ACK ESC; debounced */
void keys_repeat(bool enable);
#endif
