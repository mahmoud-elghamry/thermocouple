# Murphy TDXM — a commercial 24-channel engine pyrometer, for reference

Photos taken by the owner on 2026-10-08 of boards from a commercial engine
temperature scanner. They are kept as a design reference for REV A3
(`docs/decisions/0030`). **They are reference only, not a source to copy.**

| File | What it shows |
|---|---|
| `photo-1.jpg` | Display board, solder side (raw PCB 10-05-1281 rev C): 2x17 connector to the input board, through-hole LCD pins |
| `photo-2.jpg` | Display board, component side ("F.W. MURPHY MFG."): custom 7-segment LCD (U17, backlight BL1 under it), LCD driver U7 (PCF8566-type), 44-pin MCU U8, crystal, programming header P2 |
| `photo-3.jpg` | Input board 10-00-4143 rev G1, component side: three rows of pluggable terminals TS2_A/B/C (24 channels), isolated supply block (MPD LF102S, LP2954 regulator, Coilcraft inductor), LDA111 opto-couplers, D2PAK output FETs, 28-pin parts U4-U6 (multiplexers, inferred) |
| `photo-4.jpg` | Display board, solder side close-up (raw PCB 10-05-1281 rev C) |
| `photo-5.jpg` | A second display board (raw PCB 10-05-1261 rev B): RJ-style jack JR1, 2x17 header |
| `photo-6.jpg` | A different product, "RE-25AR-DISP-R1": 16x2 character LCD module on screws, alarm LEDs, coin cell, 26-pin IDC |
| `photo-7.jpg`, `photo-8.jpg` | Input board 10-00-4143 rev G1, whole board: the terminal rows stacked side by side on one edge |

## What the manual says

From the Murphy TDXM manual
(https://www.manualsdir.com/manuals/124629/murphy-temperature-scanner_pyrometer-tdxm.html,
read 2026-10-08):
* Inputs: up to 24 type J or K thermocouples, "grounded or ungrounded". The
  manual **recommends ungrounded**: grounded probes may read wrongly because
  of ground differences.
* Scans all channels in 2 s; a tripped setpoint is detected within 2 s.
* Outputs: two FET sinks (0.5 A, 350 VDC) and one form C solid-state relay
  (0.125 A, 350 VDC / 240 VAC). These are signal-level outputs.
* 10-32 VDC supply, 750 mW maximum. RS-485 Modbus RTU slave. An open
  thermocouple drives the reading high.

## Lessons recorded for REV A3

* **One converter behind analog multiplexers** (inferred from the board):
  only one probe is connected to the measurement at a time, which is how it
  accepts both probe types.
* **Pluggable terminals in tiers along one edge** fit 24 channels into about
  12 cm of board edge.
* **Signal-level solid-state outputs** are normal for this class of device.
