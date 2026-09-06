"""Board dimensions, floor plan and the per-channel placement template.

Pure data. No pcbnew import, so it can be read without KiCad.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BOARD_FILE = ROOT / "thermocouple_8ch.kicad_pcb"
FP_ROOT = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")

BOARD_W = 250.0
BOARD_H = 140.0

# Printed on the silkscreen.  A board in a panel has to be identifiable without
# access to a repository (design review P-03); bump REV on every fabrication.
BOARD_NAME = "THERMO-8CH"
BOARD_REV = "A0"
BOARD_DATE = "2026-09"

# ---------------------------------------------------------------------------
# Floor plan
# ---------------------------------------------------------------------------
# Three separately referenced copper islands, separated by bands that carry no
# copper at all.  The bands are also emitted as KiCad rule areas so the
# autorouter cannot bridge them, and so the gap is visible to anyone reviewing
# the board rather than being an accident of where the pours happened to stop.
#
#      x=6        x=145   x=151.5                    x=208 x=214      x=244
#   +---------------+  gap  +---------------------------+ gap +----------+
#   |  SENSOR       |       |  CONTROL                  |     |          |  y=6
#   |  8x MAX31856  |       |  ATmega32A, LCD, relay,   |     | (control)|
#   |  GND_SENS     |       |  24 V input, GND_CTRL     |     |          |
#   |  +3V3_SENS    |       |  +5V_CTRL                 |     |          |  y=107
#   |               |       |                     ------+-----+----------+
#   |               |       |                     |  gap band            |  y=113
#   |               |       |                     |     RS-485 island    |
#   +---------------+       +---------------------+     GND_RS485        |  y=134
#
SENSOR_X1 = 145.0          # right edge of the sensor island copper
CONTROL_X0 = 151.5         # left edge of the control island copper
CONTROL_X1 = 244.0
CONTROL_SPLIT_X = 208.0    # below RS485_Y0 the control island stops here
RS485_X0 = 214.0
RS485_Y0 = 99.0
CONTROL_LOWER_Y = 93.0     # above this the control island spans the full width
ZONE_TOP = 6.0
ZONE_BOTTOM = 134.0
ZONE_LEFT = 6.0

# Chassis / PE ring: a B.Cu loop 3 mm inside the board edge, bonded to the four
# plated M3 mounting holes and to J1.3 / J4.4 / the eight JTC shield screws.
# It is a separate net from all three signal grounds on purpose - a shield
# current must not become a measurement ground loop.
RING_INSET = 3.0
RING_WIDTH = 0.8

# Channel block geometry.  dx is measured from the block origin X0.
BLOCK_PITCH = 30.0
BLOCK_X0 = 9.0
BLOCK_W = 20.0

# (dx, dy, rotation) for one measurement channel in the "top" orientation.
#
# The MAX31856 is rotated 270 deg so that its analogue pins face the terminal
# block in the order the terminal presents them: T+ lands on the centre pad and
# T- on the two pads immediately to its right.  With the part at 0 deg the two
# thermocouple traces had to cross, which either costs a via in a microvolt
# path or breaks the length match between T+ and T-.
#
# R_p/R_n and C_cm_p/C_cm_n are mirrored about the T+/T- centreline (x = 6.5)
# so common-mode energy sees the same impedance on both legs.  That balance is
# what protects the microvolt measurement from 50 Hz and VFD noise; an
# asymmetric filter converts common mode into differential mode (H-03).
CHANNEL_TEMPLATE = {
    "JTC":     (4.0,  7.00,   0),   # pin1 T+, pin2 T-, pin3 shield
    "R_p":     (4.0,  14.00,  90),  # 100R 0.1% in series with T+
    "R_n":     (9.0,  14.00,  90),  # 100R 0.1% in series with T-
    "C_cm_p":  (2.0,  17.20,  0),   # 10n C0G, T+ to GND_SENS
    "C_diff":  (6.5,  17.20,  0),   # 100n C0G across T+/T-
    "C_cm_n":  (11.0, 17.20,  0),   # 10n C0G, T- to GND_SENS
    "U":       (6.5,  22.90,  270),
    # AVDD is pin 5 (top row) and DVDD is pin 8 (bottom row), both on the left
    # half of the rotated package, so both bypass capacitors sit in a column
    # beside them: 3.8 mm and 2.6 mm from their pins.
    "C_avdd":  (2.2,  21.10,  270),  # 270 puts pad 1 (+3V3) nearest pin 5
    "C_dvdd":  (2.2,  24.70,  90),
    "R_cs":    (2.5,  28.50,  0),   # 10k pull-up so CS is high before init
    "R_miso":  (8.0,  28.50,  0),   # 100R series on the shared MISO bus
}
