#ifndef FAMILY_IMAGE_IDENTITY_H
#define FAMILY_IMAGE_IDENTITY_H
#include "common/types.h"
/* Outside code/data; immediately below the existing far-flash CRC region.
 * Boot CRC covers code/data followed by these bytes, excluding unused holes. */
#define APP_IDENTITY_ADDRESS 0x1FF80UL
#define APP_IDENTITY_BYTES 64u
#define APP_IMAGE_VECTOR_BYTES 140u /* ATmega1284P: 35 four-byte vectors */
#define APP_IDENTITY_MAGIC "THFWID01"
#define APP_IDENTITY_MCU_0 0x1Eu
#define APP_IDENTITY_MCU_1 0x97u
#define APP_IDENTITY_MCU_2 0x05u
typedef struct {
    uint8_t magic[8],board,mcu[3],major,minor,patch,dirty;
    char commit[13]; /* twelve lowercase hexadecimal digits plus NUL */
    uint8_t reserved[35];
} image_identity_t;
typedef char image_identity_size_check[sizeof(image_identity_t)==APP_IDENTITY_BYTES?1:-1];
extern const image_identity_t app_image_identity;
void app_identity_read(image_identity_t *out);
#endif
