#ifndef FAMILY_TC_MATH_H
#define FAMILY_TC_MATH_H
#include "common/types.h"
/* NIST ITS-90, 10 C table: K -200..1372 C, J -210..1200 C.
 * Raw inverse permits the whole table; compensated engine reading flags < -50 C. */
res_t tc_dC_to_emf(ch_type_t type, temp_dC_t temp, emf_nV_t *out);
res_t tc_inverse(ch_type_t type, emf_nV_t emf, temp_dC_t *out);
res_t tc_emf_to_dC(ch_type_t type, emf_nV_t emf, temp_dC_t cj, temp_dC_t *out);
/* Full measurement flags, including COLD separately from RANGE. */
uint8_t tc_convert(ch_type_t type, emf_nV_t emf, temp_dC_t cj, temp_dC_t *out);
#endif
