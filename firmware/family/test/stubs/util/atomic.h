#ifndef TEST_AVR_ATOMIC_H
#define TEST_AVR_ATOMIC_H
/* Host register test is single threaded; production uses avr-libc ATOMIC_BLOCK. */
#define ATOMIC_RESTORESTATE 0
#define ATOMIC_BLOCK(type) for(unsigned atomic_once=1;atomic_once;atomic_once=0)
#endif
