#include "drivers/keys.h"
#include "board/board_cfg.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include <string.h>
static volatile uint8_t history[5];
static volatile uint8_t stable;
static uint8_t previous,armed,delivered,pending,press_edges;
static uint32_t since[5],repeat_at[2];
static bool chord,repeating;
static key_event_t queue[8]; static uint8_t head,tail;
static void emit(key_t key,uint32_t press,uint32_t now) {
    uint8_t n=(uint8_t)((head+1)&7);
    if(n!=tail) { queue[head].key=key; queue[head].pressed_ms=press; queue[head].event_ms=now; head=n; }
}
/* Gesture rearming must not erase a physical abort edge from this pass. */
void keys_rearm(void) { armed=0; pending=0; delivered=0; chord=false; head=tail=0; }
uint8_t keys_pressed(void) { uint8_t p=press_edges; press_edges=0; return p; }
void keys_init(void) {
    uint8_t i; for(i=0;i<5;i++) history[i]=0xFF;
    memset(since,0,sizeof since);
    stable=previous=press_edges=0; repeating=false; keys_rearm();
}
void keys_sample_isr(void) {
    uint8_t i;
    for(i=0;i<board()->key_count;i++) {
        history[i]=(uint8_t)((history[i]<<1)|(gpio_read(board()->keys[i])?1u:0u));
        if(history[i]==0) stable|=(uint8_t)(1u<<i);
        else if(history[i]==255) stable&=(uint8_t)~(1u<<i);
    }
}
uint8_t keys_held(void) { return stable; }
void keys_repeat(bool e) { repeating=e; }
void keys_task(void) {
    uint8_t s=stable,i; uint32_t now=tick_ms();
    press_edges=(uint8_t)(s&~previous);
    for(i=0;i<board()->key_count;i++) {
        uint8_t bit=(uint8_t)(1u<<i);
        if(!(s&bit) && !(previous&bit) && history[i]==255) armed|=bit;
        if((s&bit) && !(previous&bit)) {
            since[i]=now; delivered&=(uint8_t)~bit;
            if((armed&bit) && i<2) { pending|=bit; repeat_at[i]=now+600; }
        }
        if((s&bit) && now-since[i]>30000) { armed&=(uint8_t)~bit; pending&=(uint8_t)~bit; }
    }
    if((s&3)==3 && (pending&3)!=0 && (armed&3)==3 &&
       ((since[0]>since[1]?since[0]-since[1]:since[1]-since[0])<=150)) {
        chord=true; pending&=0xFC;
    }
    for(i=0;i<board()->key_count;i++) {
        uint8_t bit=(uint8_t)(1u<<i); uint32_t held=now-since[i];
        if(!(armed&bit)) continue;
        if((s&bit) && i==3 && held>=50 && !(delivered&bit)) { emit(KEY_ACK,since[i],now); delivered|=bit; }
        if(i<2 && !chord) {
            if((pending&bit) && (held>=150 || !(s&bit))) {
                emit(i==0?KEY_UP:KEY_DOWN,since[i],now); pending&=(uint8_t)~bit; delivered|=bit;
            }
            if(repeating && (s&bit) && (int32_t)(now-repeat_at[i])>=0) {
                emit(i==0?KEY_UP:KEY_DOWN,since[i],now); repeat_at[i]=now+(held>=3000?50u:150u);
            }
        }
        if(!(s&bit) && (previous&bit)) {
            if(i==2) emit(held>=3000?KEY_SET_LONG:KEY_SET,since[i],now);
            if(i==4) emit(KEY_ESC,since[i],now);
            armed&=(uint8_t)~bit;
        }
    }
    if(chord && !(s&3)) { emit(KEY_ESC,since[0],now); chord=false; }
    previous=s;
}
bool keys_get_event(key_event_t *event) {
    uint8_t i;
    for(i=0;i<7 && tail!=head;i++) {
        key_event_t e=queue[tail]; tail=(uint8_t)((tail+1)&7);
        if(e.key!=KEY_ACK || tick_ms()-e.event_ms<=500) { *event=e; return true; }
    }
    return false;
}
key_t keys_get(void) { key_event_t e; return keys_get_event(&e)?e.key:KEY_NONE; }
