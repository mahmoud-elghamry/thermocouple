/* Real production debounce/gesture driver feeding the standalone UI. */
#include "fake_ui.h"
#include "board/board_cfg.h"
#include <stdio.h>
#include <string.h>
static uint8_t held;
static unsigned checks,failures,acks,shorts,longs,escs,ups;
static const board_t cfg={.channels=24,.key_count=4,.keys={0,1,2,3}};
const board_t *board(void) { return &cfg; }
bool gpio_read(pin_t pin) { return (held&(1u<<pin))==0; }
#define CHECK(x) do { checks++;if(!(x)) { failures++;printf("GESTURE FAIL line %u: %s\n",(unsigned)__LINE__,#x); } } while(0)
static bool has(const char *s) { char f[81];memcpy(f,fake_frame,80);f[80]=0;return strstr(f,s)!=NULL; }
static void sample(uint8_t mask,unsigned ms) {
    unsigned i;key_event_t e; held=mask;
    for(i=0;i<ms;i++) {
        fake_ms++;keys_sample_isr();keys_task();
        while(keys_get_event(&e)) {
            if(e.key==KEY_ACK) { acks++;CHECK(!ui_key(e.key)); }
            else {
                if(e.key==KEY_SET) shorts++;
                if(e.key==KEY_SET_LONG) longs++;
                if(e.key==KEY_ESC) escs++;
                if(e.key==KEY_UP) ups++;
                CHECK(ui_key(e.key));
            }
            ui_task(1000);
        }
        ui_task(1000);
    }
}
static void reset(void) {
    held=0;fake_reset(false);keys_init();acks=shorts=longs=escs=ups=0;sample(0,12);
}
int main(void) {
    unsigned n;
    reset(); sample(4,40);CHECK(shorts==0);sample(0,12);CHECK(shorts==1 && longs==0);fake_pump();CHECK(has("CHOOSE CHANNEL"));
    reset();sample(4,3010);CHECK(longs==0);sample(0,12);fake_pump();CHECK(longs==1 && shorts==0);CHECK(has("SETUP PIN"));
    /* UP single is cancelled when DOWN joins inside 150 ms; one ESC on
     * release of BOTH, no page move and no partial chord release event. */
    reset();sample(1,50);sample(3,80);CHECK(ups==0 && escs==0);sample(2,20);CHECK(escs==0);sample(0,12);CHECK(escs==1 && ups==0);
    reset();sample(8,40);CHECK(acks==0);sample(8,30);CHECK(acks==1);sample(8,100);CHECK(acks==1);sample(0,12);
    /* A held key at boot/rearm is never an ACK until release and re-press. */
    reset();sample(8,20);keys_rearm();sample(8,100);CHECK(acks==0);sample(0,12);sample(8,70);CHECK(acks==1);
    reset();sample(1,500);n=ups;CHECK(n==1);sample(1,500);CHECK(ups==n);
    sample(0,12);sample(4,3010);sample(0,12); /* PIN is an edit field */
    n=ups;sample(1,1000);CHECK(ups>n);sample(1,2100);n=ups;sample(1,160);CHECK(ups>=n+3);
    sample(1,31000);n=ups;sample(1,1000);CHECK(ups==n);sample(0,12);sample(1,170);CHECK(ups==n+1);
    printf("UI gestures: %u checks, %u failures\n",checks,failures);return failures?1:0;
}
