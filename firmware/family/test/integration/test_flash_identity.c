/* Execute the real AVR boot-CRC state machine over register-level flash fakes. */
#include "app/image_identity.h"
#include "mcal/flash_crc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint8_t memory[131072];
static unsigned checks,reads;
#define CHECK(x) do { ++checks; if(!(x)) { printf("Flash identity FAIL %u: %s\n",(unsigned)__LINE__,#x);exit(1); } } while(0)
uint32_t fake_flash_address(const char *s) { return !strcmp(s,"__data_load_end")?512u:0x1FFFEu; }
uint8_t fake_flash_byte(uint32_t a) { CHECK(a<sizeof memory);++reads;return memory[a]; }
uint16_t fake_flash_word(uint32_t a) { uint16_t lo=fake_flash_byte(a);return (uint16_t)(lo|((uint16_t)fake_flash_byte(a+1)<<8)); }
static uint16_t update(uint16_t c,uint8_t b) {
    unsigned i;c^=(uint16_t)b<<8;
    for(i=0;i<8;i++) c=(uint16_t)((c&0x8000u)?(c<<1)^0x1021u:c<<1);
    return c;
}
static res_t run(void) {
    unsigned i;res_t r=RES_BUSY;flash_crc_begin();
    for(i=0;i<6 && r==RES_BUSY;i++) { reads=0;r=flash_crc();CHECK(reads<=130); }
    CHECK(i==5);return r;
}
int main(void) {
    unsigned i;uint16_t crc=0xFFFF;
    memset(memory,0xFF,sizeof memory);
    for(i=0;i<512;i++) { memory[i]=(uint8_t)i;crc=update(crc,memory[i]); }
    for(i=0;i<APP_IDENTITY_BYTES;i++) { memory[APP_IDENTITY_ADDRESS+i]=(uint8_t)(3*i);crc=update(crc,(uint8_t)(3*i)); }
    memory[0x1FFFE]=(uint8_t)crc;memory[0x1FFFF]=(uint8_t)(crc>>8);
    CHECK(run()==RES_OK && flash_crc_value()==crc);
    for(i=0;i<APP_IDENTITY_BYTES;i++) {
        memory[APP_IDENTITY_ADDRESS+i]^=1;CHECK(run()==RES_ERR_CRC);memory[APP_IDENTITY_ADDRESS+i]^=1;
    }
    memory[0]^=1;CHECK(run()==RES_ERR_CRC);memory[0]^=1;
    memory[511]^=1;CHECK(run()==RES_ERR_CRC);memory[511]^=1;
    memory[1000]^=1;CHECK(run()==RES_OK); /* Unprogrammed hole is deliberately excluded. */
    printf("Flash identity CRC: %u checks PASS (all identity bytes covered; bounded steps)\n",checks);
    return 0;
}
