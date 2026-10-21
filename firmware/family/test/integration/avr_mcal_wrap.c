/* Exclude register-model CPU from AVR timing. The measured application keeps
 * every real driver/service instruction; MCAL costs are bounded separately. */
#define gpio_init base_gpio_init
#define gpio_write base_gpio_write
#define gpio_read base_gpio_read
#define gpio_mask base_gpio_mask
#define delay_us base_delay_us
#define spi_init base_spi_init
#define spi_enable base_spi_enable
#define spi_xfer base_spi_xfer
#define spi_soft_xfer base_spi_soft_xfer
#define timer_init base_timer_init
#define tick_ms base_tick_ms
#define timer_run_start base_timer_run_start
#define timer_run_start_at base_timer_run_start_at
#define timer_run_stop base_timer_run_stop
#define timer_run_remaining base_timer_run_remaining
#define timer_run_active base_timer_run_active
#define timer_run_expired base_timer_run_expired
#define timer_run_ack_expiry base_timer_run_ack_expiry
#define timer_run_static_high base_timer_run_static_high
#define wdt_feed base_wdt_feed
#define reset_cause base_reset_cause
#define fuses_read base_fuses_read
#define fuses_ok base_fuses_ok
#define flow_check base_flow_check
#define ee_read base_ee_read
#define ee_ready base_ee_ready
#define ee_write_byte base_ee_write_byte
#define uart_init base_uart_init
#define uart_put base_uart_put
#define uart_get base_uart_get
#define uart_tx_complete base_uart_tx_complete
#include "fake_mcal.c"
#undef gpio_init
#undef gpio_write
#undef gpio_read
#undef gpio_mask
#undef delay_us
#undef spi_init
#undef spi_enable
#undef spi_xfer
#undef spi_soft_xfer
#undef timer_init
#undef tick_ms
#undef timer_run_start
#undef timer_run_start_at
#undef timer_run_stop
#undef timer_run_remaining
#undef timer_run_active
#undef timer_run_expired
#undef timer_run_ack_expiry
#undef timer_run_static_high
#undef wdt_feed
#undef reset_cause
#undef fuses_read
#undef fuses_ok
#undef flow_check
#undef ee_read
#undef ee_ready
#undef ee_write_byte
#undef uart_init
#undef uart_put
#undef uart_get
#undef uart_tx_complete
volatile uint8_t profile_kind;
volatile uint16_t profile_arg;
static uint8_t depth;
__attribute__((noinline)) void profile_io_begin(void) { __asm__ volatile("nop"); }
__attribute__((noinline)) void profile_io_end(void) { __asm__ volatile("nop"); }
static void enter(uint8_t kind,uint16_t arg) {
    if(depth++==0) { profile_kind=kind; profile_arg=arg; profile_io_begin(); }
}
static void leave(void) { if(--depth==0) profile_io_end(); }
#define WRAPPER __attribute__((noinline,noclone,optimize("no-optimize-sibling-calls")))
#define RET(t,n,a,c,k,p) WRAPPER t n a { t result; enter(k,p); result=base_##n c; leave(); return result; }
#define VOID(n,a,c,k,p) WRAPPER void n a { enter(k,p); base_##n c; leave(); }
VOID(gpio_init,(void),(),1,0)
VOID(gpio_write,(pin_t p,bool h),(p,h),2,p)
RET(bool,gpio_read,(pin_t p),(p),3,p)
VOID(gpio_mask,(uint8_t p,uint8_t m,uint8_t v),(p,m,v),4,p)
VOID(delay_us,(uint16_t u),(u),5,u)
VOID(spi_init,(void),(),6,0)
VOID(spi_enable,(bool e),(e),7,0)
RET(res_t,spi_xfer,(uint8_t t,uint8_t *r),(t,r),8,0)
RET(uint8_t,spi_soft_xfer,(uint8_t t),(t),9,0)
VOID(timer_init,(void),(),10,0)
RET(uint32_t,tick_ms,(void),(),11,0)
VOID(timer_run_start,(uint16_t d),(d),12,d)
RET(bool,timer_run_start_at,(uint16_t d,uint32_t a),(d,a),13,d)
VOID(timer_run_stop,(void),(),14,0)
RET(uint16_t,timer_run_remaining,(void),(),15,0)
RET(bool,timer_run_active,(void),(),16,0)
RET(bool,timer_run_expired,(void),(),17,0)
VOID(timer_run_ack_expiry,(void),(),18,0)
VOID(timer_run_static_high,(void),(),19,0)
VOID(wdt_feed,(void),(),20,0)
RET(uint8_t,reset_cause,(void),(),21,0)
VOID(fuses_read,(uint8_t *f),(f),22,0)
RET(bool,fuses_ok,(void),(),23,0)
RET(bool,flow_check,(uint8_t s,uint8_t e,uint32_t p),(s,e,p),24,0)
RET(uint8_t,ee_read,(uint16_t a),(a),25,0)
RET(bool,ee_ready,(void),(),26,0)
RET(res_t,ee_write_byte,(uint16_t a,uint8_t v),(a,v),27,0)
VOID(uart_init,(void),(),28,0)
RET(bool,uart_put,(uint8_t b),(b),29,0)
RET(bool,uart_get,(uint8_t *b),(b),30,0)
RET(bool,uart_tx_complete,(void),(),31,0)
