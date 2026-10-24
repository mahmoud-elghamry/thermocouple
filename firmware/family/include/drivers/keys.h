#ifndef FAMILY_KEYS_H
#define FAMILY_KEYS_H
#include "common/types.h"
typedef enum { KEY_NONE, KEY_UP, KEY_DOWN, KEY_SET, KEY_ACK, KEY_ESC, KEY_SET_LONG } key_t;
typedef struct { key_t key; uint32_t pressed_ms,event_ms; } key_event_t;
void keys_init(void);
void keys_sample_isr(void);
void keys_task(void);
key_t keys_get(void);
bool keys_get_event(key_event_t *event); /* authoritative press + emission times */
uint8_t keys_pressed(void); /* newly debounced press edges from this task pass */
void keys_rearm(void);
uint8_t keys_held(void); /* bits UP DOWN SET ACK ESC; debounced */
void keys_repeat(bool enable);
#endif
