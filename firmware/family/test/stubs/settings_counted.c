/* Count whole-record validations in the real shell without changing settings. */
#define set_validate counted_validate_impl
#include "../../src/services/settings.c"
#undef set_validate
static unsigned validations;
res_t set_validate(const settings_t *cfg) { ++validations; return counted_validate_impl(cfg); }
unsigned settings_validation_count(void) { unsigned n=validations; validations=0; return n; }
