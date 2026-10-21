#ifndef FAMILY_ACQUISITION_BUDGET_H
#define FAMILY_ACQUISITION_BUDGET_H
#include "common/types.h"
/* Shell scheduling seam: one of the 19 mutable ADC checks per bank/pass.
 * The original full verification API remains available to standalone callers. */
res_t ad_verify_mutable_part(uint8_t bank,uint8_t index);
#endif
