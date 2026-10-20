#include "services/tc_math.h"
#include "services/tc_tables.h"
#include "common/meas.h"
#include <stddef.h>
res_t tc_dC_to_emf(ch_type_t type, temp_dC_t temp, emf_nV_t *out)
{
    uint16_t n=tc_table_count(type), i; int32_t span, offset; int64_t delta;
    if(out==NULL) return RES_ERR_RANGE;
    *out=0;
    if(n<2 || temp<tc_table_temp(type,0) || temp>tc_table_temp(type,(uint16_t)(n-1u))) return RES_ERR_RANGE;
    i=(uint16_t)(((int32_t)temp-tc_table_temp(type,0))/100);
    if(i>=n-1u) { *out=tc_table_emf(type,(uint16_t)(n-1u)); return RES_OK; }
    span=(int32_t)tc_table_temp(type,(uint16_t)(i+1u))-tc_table_temp(type,i);
    offset=(int32_t)temp-tc_table_temp(type,i);
    delta=(int64_t)(tc_table_emf(type,(uint16_t)(i+1u))-tc_table_emf(type,i))*offset;
    *out=tc_table_emf(type,i)+(int32_t)((delta+span/2)/span); return RES_OK;
}
res_t tc_inverse(ch_type_t type, emf_nV_t emf, temp_dC_t *out)
{
    uint16_t n=tc_table_count(type), lo=0, hi; uint8_t step;
    int32_t base, span, tspan; int64_t offset;
    if(out==NULL) return RES_ERR_RANGE;
    *out=TEMP_DC_INVALID;
    if(n<2) return RES_ERR_RANGE;
    hi=(uint16_t)(n-1u);
    if(emf<tc_table_emf(type,0) || emf>tc_table_emf(type,hi)) return RES_ERR_RANGE;
    if(emf==tc_table_emf(type,hi)) { *out=tc_table_temp(type,hi); return RES_OK; }
    for(step=0;step<9 && (uint16_t)(hi-lo)>1u;++step) {
        uint16_t mid=(uint16_t)(lo+(hi-lo)/2u);
        if(tc_table_emf(type,mid)<=emf) lo=mid; else hi=mid;
    }
    if((uint16_t)(hi-lo)!=1u) return RES_ERR_RANGE;
    base=tc_table_emf(type,lo); span=tc_table_emf(type,hi)-base;
    tspan=(int32_t)tc_table_temp(type,hi)-tc_table_temp(type,lo);
    offset=(int64_t)(emf-base)*tspan;
    *out=(temp_dC_t)(tc_table_temp(type,lo)+(int32_t)((offset+span/2)/span)); return RES_OK;
}
uint8_t tc_convert(ch_type_t type, emf_nV_t emf, temp_dC_t cj, temp_dC_t *out)
{
    emf_nV_t e_cj; int64_t sum; temp_dC_t t;
    if(out==NULL) return MEAS_RANGE;
    *out=TEMP_DC_INVALID;
    if(tc_dC_to_emf(type,cj,&e_cj)!=RES_OK) return MEAS_RANGE;
    sum=(int64_t)emf+e_cj;
    if(sum<INT32_MIN || sum>INT32_MAX || tc_inverse(type,(int32_t)sum,&t)!=RES_OK) return MEAS_RANGE;
    if(t<-500) return MEAS_COLD;
    *out=t; return MEAS_VALID;
}
res_t tc_emf_to_dC(ch_type_t type, emf_nV_t emf, temp_dC_t cj, temp_dC_t *out)
{ return tc_convert(type,emf,cj,out)==MEAS_VALID?RES_OK:RES_ERR_RANGE; }
