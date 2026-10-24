#include "mcal/wdt.h"
#include "mcal/timer.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <avr/boot.h>
static uint8_t cause __attribute__((section(".noinit")));
/* avr-libc emits the timed writes within four cycles, with IRQs masked. */
void early_init(void) __attribute__((naked,section(".init3"),used));
void early_init(void) {
    cli(); __asm__ __volatile__("wdr"); cause=MCUSR; MCUSR=0;
    wdt_enable(WDTO_250MS); MCUCR|=_BV(JTD); MCUCR|=_BV(JTD);
    PORTB&=(uint8_t)~8u; DDRB|=8;
}
void wdt_init(void) { wdt_enable(WDTO_250MS); } /* OPEN-H5: measure actual timeout */
void wdt_feed(void) { __asm__ __volatile__("wdr"); }
uint8_t reset_cause(void) { return cause; }
void fuses_read(uint8_t f[3]) {
    uint8_t s=SREG; cli();
    f[0]=boot_lock_fuse_bits_get(GET_LOW_FUSE_BITS);
    f[1]=boot_lock_fuse_bits_get(GET_HIGH_FUSE_BITS);
    f[2]=boot_lock_fuse_bits_get(GET_EXTENDED_FUSE_BITS); SREG=s;
}
bool fuses_ok(void) { uint8_t f[3]; fuses_read(f); return f[0]==0xF7 && f[1]==0xC1 && (f[2]&7)==4; }
bool flow_check(uint8_t seen,uint8_t expected,uint32_t p) {
    if(seen!=expected || tick_ms()-p>100) return false;
    wdt_feed(); return true;
}
