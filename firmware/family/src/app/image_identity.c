#include "app/image_identity.h"
#include "app/version.h"
#include <string.h>
#ifdef FAMILY_PRODUCTION_IDENTITY
#include "identity_generated.h"
#else
/* Host/register-model fixtures have an explicit non-production identity. */
#define FAMILY_BUILD_HASH "000000000000"
#define FAMILY_BUILD_DIRTY 1
#endif
#if defined(__AVR__) && !defined(FAMILY_REGISTER_MODEL)
#include <avr/io.h>
#include <avr/pgmspace.h>
_Static_assert(APP_IMAGE_VECTOR_BYTES==_VECTORS_SIZE,"Target vector table mismatch");
#define IDENTITY_STORAGE __attribute__((section(".image_identity"),used,externally_visible))
#else
#define IDENTITY_STORAGE
#endif
const image_identity_t app_image_identity IDENTITY_STORAGE={
    /* Exactly eight bytes without NUL; tests/validator compare the shared magic. */
    {'T','H','F','W','I','D','0','1'},24,{APP_IDENTITY_MCU_0,APP_IDENTITY_MCU_1,APP_IDENTITY_MCU_2},
    (uint8_t)(FW_BUILD_VERSION>>8),(uint8_t)(FW_BUILD_VERSION&0xFFu),FW_BUILD_PATCH,
    FAMILY_BUILD_DIRTY,FAMILY_BUILD_HASH,{0}
};
void app_identity_read(image_identity_t *out) {
#if defined(__AVR__) && !defined(FAMILY_REGISTER_MODEL)
    uint8_t i,*p=(uint8_t *)out;
    for(i=0;i<APP_IDENTITY_BYTES;i++) p[i]=pgm_read_byte_far(APP_IDENTITY_ADDRESS+i);
#else
    memcpy(out,&app_image_identity,sizeof *out);
#endif
}
