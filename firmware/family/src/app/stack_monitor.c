#include "app/stack_monitor.h"
#include "app/stack_budget.h"
#ifdef __AVR__
#include <avr/io.h>
extern uint8_t __heap_start;
/* S0 is in .init3; .init4 then initializes data/BSS. Paint in .init5,
 * before constructors/main and with no active C stack frames. Section order
 * guarantees S0 precedes painting regardless of source/link order.
 * __heap_start follows .noinit, which must retain the reset cause.
 * Only free SRAM is touched, so initialized data/BSS remain intact. */
void app_stack_paint(void) __attribute__((naked,used,section(".init5")));
void app_stack_paint(void) {
    __asm__ volatile(
        "ldi r26,lo8(__heap_start)\n\t"
        "ldi r27,hi8(__heap_start)\n\t"
        "ldi r30,lo8(%0)\n\t"
        "ldi r31,hi8(%0)\n\t"
        "ldi r24,0xa5\n"
        "1: st X+,r24\n\t"
        "cp r26,r30\n\t"
        "cpc r27,r31\n\t"
        "brne 1b\n\t" : : "n" (RAMEND+1));
}
static uint16_t cursor,highwater;
static uint16_t bottom(void) {
    uint16_t low=RAMEND+1u-APP_STACK_BYTES;
    return (uint16_t)(uintptr_t)&__heap_start>low?(uint16_t)(uintptr_t)&__heap_start:low;
}
void app_stack_step(void) {
    uint8_t i;
    if(cursor<bottom() || cursor>RAMEND) cursor=bottom();
    for(i=0;i<16 && cursor<=RAMEND;i++,cursor++) {
        if(*(volatile uint8_t *)(uintptr_t)cursor!=0xa5) {
            uint16_t used=RAMEND+1u-cursor;
            if(used>highwater) highwater=used;
            cursor=bottom(); return;
        }
    }
}
uint16_t app_stack_highwater(void) { return highwater; }
#ifdef FAMILY_REGISTER_MODEL
uint16_t app_stack_capacity(void) { return RAMEND+1u-bottom(); }
void app_stack_refresh(void) {
    uint8_t i;
    cursor=bottom();
    for(i=0;i<APP_STACK_BYTES/16u+1u;i++) app_stack_step();
}
#endif
#else
void app_stack_step(void) { }
uint16_t app_stack_highwater(void) { return 0; }
#endif
