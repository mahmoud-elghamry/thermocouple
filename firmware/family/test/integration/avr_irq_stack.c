/* Measure the real ISR overlay independently of application call depth. */
#include <avr/io.h>
#include <stdint.h>
void profile_interrupt(uint8_t pins);
volatile uint16_t irq_stack_bytes,irq_stack_errors;
__attribute__((noinline,used)) void irq_stack_done(void) { for(;;) __asm__ volatile("nop"); }
__attribute__((noinline)) static uint8_t probe(uint8_t pins) {
    uint16_t base=SP; uint8_t i;
    /* Below the current frame only; the caller/return address is preserved. */
    for(i=0;i<64;i++) *(volatile uint8_t *)(base-63u+i)=0xa5;
    profile_interrupt(pins);
    for(i=0;i<64;i++) if(*(volatile uint8_t *)(base-63u+i)!=0xa5) return (uint8_t)(64u-i);
    return 0;
}
int main(void) {
    uint16_t i; uint8_t n;
    /* All key histories, RX full-ring/loss, and normal receive branches. */
    for(i=0;i<256;i++) {
        n=probe((uint8_t)i);
        if(n>irq_stack_bytes) irq_stack_bytes=n;
        if(!n || n>=64) ++irq_stack_errors;
    }
    irq_stack_done();
}
