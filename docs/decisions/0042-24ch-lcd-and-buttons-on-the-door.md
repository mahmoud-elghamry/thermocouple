# 0042 - 24-ch: LCD and buttons on the door, accessories bought in Egypt

* Status: accepted (owner, 2026-10-15: "you choose; available in Egypt; keep it simple")
* Date: 2026-10-15
* Builds on: `0031` D4 (LCD bought locally), `0034` D2 (five buttons, panel header), I-091, I-122

## Context

The board's LCD holes H6-H9 put a standard 2004A module over J503 (panel-button XH header), and the plugged XH
housing with its wires is about as tall as the gap under a module on a 1x16 header (review C-2, D-4). The
operator also has to read and ACK; whether opening the door for that is acceptable was open (I-091).

## Decision

LCD and buttons go on the panel door; no board change.

* LCD: standard 2004A, parallel (no I2C backpack), male header soldered on the module; 16-wire female-female
  2.54 mm cable 30-40 cm to J502 (already a male header in the BOM). M3 standoffs to the door behind a window.
* Buttons: 5 x LA38 22 mm momentary NO (ACK red) on the door, wired to J503 by an XH 6-pin pigtail.
* Enclosure: the existing generator panel, or a local steel wall box ~300x300x150 with a gland plate.
* TC wiring: screened KX extension cable straight to the pluggable terminals; mini-K plugs only if the probes
  already end in one.
* Sources (Makers Electronics, ram-e-shop, Cairo instrumentation/panel shops): `hardware/24ch/accessories.csv`.

Rejected: LCD on the board's standoffs - J503 fouls and the door must be opened to read; a wide-temperature
LCD - not sold locally, and the LCD is not in the trip path (a slow or dim display at 60 degC is cosmetic);
moving J503 - a board change for a mounting problem.

## Consequences

* The female header row (C350305) is no longer needed. Parallel HD44780 over 40 cm at firmware-paced timing is
  fine; keep the cable away from the relay and supply wiring.
* I-122 (door cut-out) is drawn from the bought LCD and buttons.
