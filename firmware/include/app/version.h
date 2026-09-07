#ifndef APP_VERSION_H
#define APP_VERSION_H

/* Firmware identity (I-023).
 *
 * The board silkscreen carries THERMO-8CH REV A0 2026-09.  Until this existed
 * a programmed unit carried nothing at all: there was no way to tell which
 * image was on a chip, or whether it matched the board it was sitting in.
 *
 * APP_TARGET_BOARD must match the silkscreen of the board the image is for.
 * Bump APP_FIRMWARE_VERSION on every change that leaves this repository.
 * Both are shown on the LCD at boot and are 16 characters or fewer.
 */

#define APP_FIRMWARE_VERSION "FW 0.2.0"
#define APP_TARGET_BOARD     "THERMO-8CH REV A0"

/* Shown on the second LCD line at boot: converter, version. */
#define APP_BOOT_BANNER      "8CH " APP_FIRMWARE_VERSION

#endif
