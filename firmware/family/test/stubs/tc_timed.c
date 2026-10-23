/* Real thermocouple math plus optional elapsed CPU time in the host model. */
#include "../integration/model.h"
#define tc_convert untimed_tc_convert
#include "../../src/services/tc_math.c"
#undef tc_convert
static uint16_t cost;
void model_tc_cost(uint16_t us) { cost=us; }
uint8_t tc_convert(ch_type_t type,emf_nV_t emf,temp_dC_t cj,temp_dC_t *out) {
    if(type!=CH_TYPE_OFF && cost) model_cpu_us(cost);
    return untimed_tc_convert(type,emf,cj,out);
}
