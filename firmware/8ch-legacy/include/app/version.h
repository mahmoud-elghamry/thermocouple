#ifndef APP_VERSION_H
#define APP_VERSION_H

/* Firmware identity (I-023).
 *
 * The board silkscreen carries THERMO-8CH REV A2 2026-09 (BOARD_REV and
 * BOARD_DATE in hardware/8ch/board/config.py).  Until this existed
 * a programmed unit carried nothing at all: there was no way to tell which
 * image was on a chip, or whether it matched the board it was sitting in.
 *
 * APP_TARGET_BOARD must match the silkscreen of the board the image is for.
 * Bump APP_FIRMWARE_VERSION on every change that leaves this repository.
 * Both are shown on the LCD at boot and are 16 characters or fewer: the LCD
 * driver cuts a line at 16, so the silkscreen's "REV A2" is written "REVA2"
 * here.  The full "THERMO-8CH REV A2" is 17 characters and would lose its
 * last one - the revision digit this string exists to show (I-070).
 */

#define APP_FIRMWARE_VERSION "FW 0.2.1"
#define APP_TARGET_BOARD     "THERMO-8CH REVA2"

/* Shown on the second LCD line at boot: converter, version. */
#define APP_BOOT_BANNER      "8CH " APP_FIRMWARE_VERSION

_Static_assert(sizeof(APP_TARGET_BOARD) - 1u <= 16u,
               "APP_TARGET_BOARD must fit one 16-character LCD line");
_Static_assert(sizeof(APP_BOOT_BANNER) - 1u <= 16u,
               "APP_BOOT_BANNER must fit one 16-character LCD line");

#endif
