#ifndef FAMILY_MODBUS_H
#define FAMILY_MODBUS_H
#include "app/app.h"
#include "mcal/uart.h"
#include <stddef.h>

#define MB_TX_BYTES 256u
#define MB_MAX_REGISTERS 64u
#define MB_BITMAP_BYTES ((MAX_CHANNELS+7u)/8u)
#define MB_RX_ERROR 1u

/* Read-only application adapter inputs missing from app.h. No defaults: version
 * comes from the build, feedback is actual sampled coil drive, and trip_latched
 * is the protection owner's persistent channel bitmap (bit 0 = channel 1).
 * uptime_s is a full u32 seconds counter, not wrapped tick_ms()/1000. */
typedef struct {
    uint32_t now_ms, uptime_s, power_cycles;
    uint16_t version, patch, schema;
    bool run_driven, alarm_driven;
    uint8_t trip_latched[MB_BITMAP_BYTES];
} mb_status_t;
/* Optional derived values for a verified immutable source epoch. Pure callers
 * normally leave snapshot.cache NULL. The shell prepares this incrementally. */
typedef struct {
    uint8_t state[MAX_CHANNELS];
    uint16_t faults[8], alarms;
} mb_map_cache_t;

/* Borrowed immutable views, valid for ONE synchronous builder invocation.
 * Cooperative owners cannot mutate these while mb_build runs. age[ch] is scans
 * since last valid result, UINT16_MAX if never valid. The shell retains a view
 * only while its settings/scan/fault generations and protection evidence remain
 * identical; it discards partial responses on any relevant change.
 * Pure callers may use a fake snapshot independently of the application. */
typedef struct {
    const settings_t *settings;
    const scan_out_t *scan;
    const prot_state_t *protection;
    const fault_registry_t *faults;
    const uint16_t *age;
    mb_status_t status;
    uint32_t last_validated_ms;
    bool have_validated;
    ack_reason_t ack_reason;
    const mb_map_cache_t *cache;
} mb_snapshot_t;

/* CRC16/Modbus: reflected A001, initial FFFF; low byte transmitted first. */
uint16_t mb_crc16(const uint8_t *data, uint16_t length);
/* Pure frame builder; returns response length, or 0 for silent discard/capacity
 * failure. Request 4..256 B; response <=133 B. In-place request == response OK.
 * Quantity 0 or >64 -> exception 03; unsupported functions -> 01; holes ->02.
 * Only physically present channels have channel/name registers. */
uint16_t mb_build(const mb_snapshot_t *snapshot, const uint8_t *request,
                  uint16_t length, uint8_t *response, uint16_t capacity);

void mb_init(void); /* after app/scan init; no I/O, starts in silent resync */
/* budget in us: calls below 1000 do no work; otherwise a bounded <=1ms step.
 * Drain <=8 RX entries, process <=one request; no blocking TX. Call every loop.
 * Normal mode owns UART exclusively; service's textual RS485 must be excluded. */
void mb_task(uint16_t budget_us);

/* Required link-time driver/application seams. Not provided by current drivers.
 * All calls nonblocking, O(1), except status (small fixed copy). The standalone
 * F3 harness reserves an estimated 2000 seam/ISR cycles. F4's deferred timestamp
 * expansion exceeds that flat estimate on an eight-pop step; its integrated
 * profiler charges actual MCAL bounds and gates the WHOLE task at 8000 cycles,
 * including Timer2 and two RX interrupts (07 section 2). tx_start rejects pending RX.
 * Configure UART0 8N2 at baud_code 0=9600, 1=19200, flush old RX/errors on change.
 * RX ring >=64 entries, one consumer. Every entry is RX-complete byte+timestamp
 * in monotonic u32 microseconds (50us quantisation), flags on FE/DOR/UPE OR ring
 * overflow, including loss with no later byte. Overflow must invalidate queued
 * bytes, never join fragments. now_us shares the RX epoch and is atomic; it must
 * extend Timer1 using the ms tick (raw 16-bit TCNT1 wraps in 65.536ms).
 * rx is an atomic pop; now_us must not precede a just-popped timestamp.
 * tx_start borrows bytes until !tx_busy; UDRE sends binary, DE before first
 * byte and release ONLY after final TXC. Suppress local echo. Busy covers DE.
 * status is a read-only application adapter, never a protection command. */
typedef uart_sample_t mb_rx_t; /* one canonical timestamped RX value, no second copy */
void mb_io_configure(uint8_t baud_code);
uint32_t mb_io_now_us(void);
bool mb_io_rx(mb_rx_t *entry);
bool mb_io_tx_start(const uint8_t *bytes, uint16_t length);
bool mb_io_tx_busy(void);
void mb_io_status(mb_status_t *status);
#endif
