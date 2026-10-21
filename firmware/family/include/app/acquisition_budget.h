#ifndef FAMILY_ACQUISITION_BUDGET_H
#define FAMILY_ACQUISITION_BUDGET_H
#include "common/types.h"
/* Shell scheduling seam: one of the 19 mutable ADC checks per bank/pass.
 * The original full verification API remains available to standalone callers. */
/* P3: poll each pending bank every pass, retain its first RDY timestamp. */
res_t ad_ready(uint8_t bank);
res_t ad_verify_mutable_part(uint8_t bank,uint8_t index);
#endif
