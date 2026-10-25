#ifndef FAMILY_APP_TIMING_H
#define FAMILY_APP_TIMING_H
/* Owner timing limits, 2026-10-23; RUN window and scan deadline 1500 ms set by the owner 2026-10-24 (I-132):
 * specs 01/2, 03/3.1+4+10, 04/5+6.1.
 * The service relay exercise has its own shorter deadline (08/1). */
#define APP_RUN_WINDOW_MS 1500u
#define APP_SCAN_DEADLINE_MS 1500u
#define APP_LOOP_BUDGET_MS 20u
#define APP_AVR_CYCLES_PER_MS 8000UL
#define APP_ADC_RDY_MIN_MS 36u
#define APP_ADC_RDY_MAX_MS 69u
#define APP_SERVICE_RELAY_MS 1000u
/* Service check P15 (08/3, I-138): scan gap incl. the REF self-test, worst ~1.07 s (03/10.2); a bench
 * limit with margin, kept below the 1500 ms G05 deadline. Not a protection limit. */
#define APP_SERVICE_SCAN_MS 1200u
#endif
