#ifndef SETTINGS_BYTES_H
#define SETTINGS_BYTES_H
#include <stdint.h>
static inline uint16_t get16(const uint8_t *p)
{ return (uint16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1]<<8)); }
static inline uint32_t get32(const uint8_t *p)
{ return (uint32_t)get16(p) | ((uint32_t)get16(p+2)<<16); }
/* Decode signed values without implementation-defined unsigned->signed overflow. */
static inline int16_t geti16(const uint8_t *p)
{ uint16_t u=get16(p); return (int16_t)((u<=INT16_MAX)?(int32_t)u:(int32_t)u-65536L); }
static inline int32_t geti32(const uint8_t *p)
{ uint32_t u=get32(p); return u<=INT32_MAX?(int32_t)u:-1-(int32_t)(UINT32_MAX-u); }
static inline void put16(uint8_t *p, uint16_t n)
{ p[0]=(uint8_t)n; p[1]=(uint8_t)(n>>8); }
static inline void put32(uint8_t *p, uint32_t n)
{ put16(p,(uint16_t)n); put16(p+2,(uint16_t)(n>>16)); }
#endif
