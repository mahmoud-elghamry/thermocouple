#include "app/ui.h"
#include <string.h>

/* Decimal conversion by bounded subtraction: no divide/modulo library calls
 * in the refresh path on the eight-bit target. */
UI_NO_RAM_TABLE void ui_number(char *out,uint8_t width,int32_t value,bool zero) {
    uint32_t magnitude=value<0?(uint32_t)(-(value+1))+1u:(uint32_t)value;
    uint32_t power=UINT32_C(1000000000);
    uint8_t i,digit; bool started=false,negative=value<0;
    memset(out,zero?'0':' ',width);
    for(i=0;i<10;i++) {
        digit=0;
        while(magnitude>=power) { magnitude-=power; digit++; }
        if(digit || i==9) started=true;
        if(i>=(uint8_t)(10-width) && (started || zero)) out[i-(10-width)]=(char)('0'+digit);
        switch(i) {
        case 0:power=100000000;break; case 1:power=10000000;break;
        case 2:power=1000000;break; case 3:power=100000;break;
        case 4:power=10000;break; case 5:power=1000;break;
        case 6:power=100;break; case 7:power=10;break; default:power=1;break;
        }
    }
    if(negative && width) {
        for(i=0;i+1<width && out[i+1]==' ';i++) { }
        if(out[i]==' ') out[i]='-'; else out[0]='-';
    }
}
int16_t ui_whole(int16_t dC) {
    uint16_t n=(uint16_t)(dC<0?-(int32_t)dC:dC),q=0;
    while(n>=10000u) { n-=10000u; q+=1000u; }
    while(n>=1000u) { n-=1000u; q+=100u; }
    while(n>=100u) { n-=100u; q+=10u; }
    while(n>=10u) { n-=10u; q++; }
    return dC<0?-(int16_t)q:(int16_t)q;
}
void ui_text(char *out,uint8_t offset,const char *text) {
    uint8_t i;
    for(i=offset;i<20;i++) {
#ifdef __AVR__
        char c=(char)pgm_read_byte(text++);
#else
        char c=*text++;
#endif
        if(!c) break;
        out[i]=c;
    }
}
void ui_name(char out[6],const char name[6]) {
    uint8_t i;for(i=0;i<6;i++) {
        uint8_t c=(uint8_t)name[i];out[i]=c>=32 && c<=126?(char)c:' ';
    }
}
