#ifndef FAMILY_APP_TIMING_H
#define FAMILY_APP_TIMING_H
/* Owner timing limits, 2026-10-23; RUN window and scan deadline 1500 ms set by the owner 2026-10-24 (I-124):
 * specs 01/2, 03/3.1+4+10, 04/5+6.1.
 * The service relay exercise has its own shorter deadline (08/1). */
#define APP_RUN_WINDOW_MS 1500u
#define APP_SCAN_DEADLINE_MS 1500u
#define APP_LOOP_BUDGET_MS 20u
#define APP_AVR_CYCLES_PER_MS 8000UL
#define APP_ADC_RDY_MIN_MS 36u
#define APP_ADC_RDY_MAX_MS 69u
#define APP_SERVICE_RELAY_MS 1000u
#endif
