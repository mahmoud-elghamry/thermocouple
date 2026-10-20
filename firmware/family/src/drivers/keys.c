#include "drivers/keys.h"
#include "board/board_cfg.h"
#include "mcal/gpio.h"
#include "mcal/timer.h"
#include <string.h>
static volatile uint8_t history[5];
static volatile uint8_t stable;
static uint8_t previous,armed,delivered,pending;
static uint32_t since[5],repeat_at[2];
static bool chord,repeating;
static key_t queue[8]; static uint32_t stamps[8]; static uint8_t head,tail;
static void emit(key_t key) {
    uint8_t n=(uint8_t)((head+1)&7);
    if(n!=tail) { queue[head]=key; stamps[head]=tick_ms(); head=n; }
}
void keys_rearm(void) { armed=0; pending=0; delivered=0; chord=false; head=tail=0; }
void keys_init(void) {
    uint8_t i; for(i=0;i<5;i++) history[i]=0xFF;
    memset(since,0,sizeof since);
    stable=previous=0; repeating=false; keys_rearm();
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
        if((s&bit) && i==3 && held>=50 && !(delivered&bit)) { emit(KEY_ACK); delivered|=bit; }
        if(i<2 && !chord) {
            if((pending&bit) && (held>=150 || !(s&bit))) {
                emit(i==0?KEY_UP:KEY_DOWN); pending&=(uint8_t)~bit; delivered|=bit;
            }
            if(repeating && (s&bit) && (int32_t)(now-repeat_at[i])>=0) {
                emit(i==0?KEY_UP:KEY_DOWN); repeat_at[i]=now+(held>=3000?50u:150u);
            }
        }
        if(!(s&bit) && (previous&bit)) {
            if(i==2) emit(held>=3000?KEY_SET_LONG:KEY_SET);
            if(i==4) emit(KEY_ESC);
            armed&=(uint8_t)~bit;
        }
    }
    if(chord && !(s&3)) { emit(KEY_ESC); chord=false; }
    previous=s;
}
key_t keys_get(void) {
    uint8_t i;
    for(i=0;i<7 && tail!=head;i++) {
        key_t k=queue[tail]; uint32_t stamp=stamps[tail]; tail=(uint8_t)((tail+1)&7);
        if(k!=KEY_ACK || tick_ms()-stamp<=500) return k;
    }
    return KEY_NONE;
}
