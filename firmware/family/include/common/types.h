/* Shared types for the family firmware. Spec: firmware/spec/00-overview.md, 10-phases.md section 1.
 * Owned by Claude; both implementation lanes include it and must not change it without review. */
#ifndef FAMILY_COMMON_TYPES_H
#define FAMILY_COMMON_TYPES_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    RES_OK = 0,
    RES_BUSY,
    RES_ERR_TIMEOUT,
    RES_ERR_CRC,
    RES_ERR_ID,
    RES_ERR_READBACK,
    RES_ERR_RANGE
} res_t;

/* Temperatures in 0.1 C, EMF in nV (00-overview "Shared conventions"). */
typedef int16_t temp_dC_t;
typedef int32_t emf_nV_t;

#define TEMP_DC_INVALID ((temp_dC_t)INT16_MIN)

/* Channel types and modes as stored in settings (05-settings-events.md 2.2). */
typedef enum { CH_TYPE_OFF = 0, CH_TYPE_K = 1, CH_TYPE_J = 2, CH_TYPE_PT100 = 3 } ch_type_t;
typedef enum { CH_MODE_TRIP = 0, CH_MODE_ALARM_ONLY = 1 } ch_mode_t;

#define MAX_CHANNELS 24u /* 24-ch board only (00 Targets, owner 2026-10-23) */
#define MAX_BANKS 3u     /* banks A-C */

#endif
