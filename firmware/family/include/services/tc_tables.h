#ifndef FAMILY_TC_TABLES_H
#define FAMILY_TC_TABLES_H
#include "common/types.h"
/* Accessor reads flash on AVR; index bounded by count. Invalid input -> 0. */
uint16_t tc_table_count(ch_type_t type);
temp_dC_t tc_table_temp(ch_type_t type, uint16_t i);
emf_nV_t tc_table_emf(ch_type_t type, uint16_t i);
#endif
