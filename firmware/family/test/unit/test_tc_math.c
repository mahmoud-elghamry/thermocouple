#include "core_test.h"
#include "services/tc_tables.h"
#include "tc_reference.h"
void test_tc_math(void)
{
    size_t i; temp_dC_t t; emf_nV_t e, cj;
    CHECK(tc_table_count(CH_TYPE_K)==159 && tc_table_count(CH_TYPE_J)==142);
    for(i=0;i<sizeof(tc_vectors)/sizeof(tc_vectors[0]);++i) {
        const tc_vector_t *v=&tc_vectors[i];
        CHECK(tc_inverse(v->type,v->emf,&t)==RES_OK);
        CHECK(abs((int)t-v->temp)<=2); /* 0.17 C interpolation + 0.05 C quantization */
        CHECK(tc_dC_to_emf(v->type,v->temp,&e)==RES_OK);
        CHECK(labs((long)e-v->emf)<=4000); /* half-step low-end interpolation, <=0.17 C */
    }
    CHECK(tc_dC_to_emf(CH_TYPE_K,1000,&e)==RES_OK && labs((long)e-4096000)<=500);
    CHECK(tc_dC_to_emf(CH_TYPE_J,1000,&e)==RES_OK && labs((long)e-5269000)<=500);
    CHECK(tc_dC_to_emf(CH_TYPE_K,250,&cj)==RES_OK);
    CHECK(tc_emf_to_dC(CH_TYPE_K,-cj,250,&t)==RES_OK && t==0);
    CHECK(tc_dC_to_emf(CH_TYPE_J,250,&cj)==RES_OK);
    CHECK(tc_emf_to_dC(CH_TYPE_J,-cj,250,&t)==RES_OK && t==0);
    CHECK(tc_convert(CH_TYPE_K,-10000000,0,&t)==MEAS_RANGE && t==TEMP_DC_INVALID);
    CHECK(tc_dC_to_emf(CH_TYPE_K,-510,&e)==RES_OK);
    CHECK(tc_convert(CH_TYPE_K,e,0,&t)==MEAS_COLD);
    CHECK(tc_convert(CH_TYPE_K,INT32_MAX,250,&t)==MEAS_RANGE);
    CHECK(tc_convert(CH_TYPE_K,INT32_MIN,250,&t)==MEAS_RANGE);
    CHECK(tc_inverse((ch_type_t)99,0,&t)!=RES_OK);
    CHECK(tc_dC_to_emf(CH_TYPE_K,13721,&e)!=RES_OK);
    CHECK(tc_inverse(CH_TYPE_K,tc_table_emf(CH_TYPE_K,158)+1,&t)!=RES_OK);
    CHECK(tc_inverse(CH_TYPE_J,tc_table_emf(CH_TYPE_J,0)-1,&t)!=RES_OK);
}
