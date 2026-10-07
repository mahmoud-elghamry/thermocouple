# 0024 — Three autonomous eight-channel modules; common shutdown

* Status: accepted; three autonomous modules agreed 2026-10-01; **common series shutdown confirmed 2026-10-07** (updates below)
* Date: 2026-09-29
* Decider: owner, explicit clarification in the review conversation
* Supersedes: the assumption that the complete product has only eight channels

## Original context (2026-09-29; resolved by updates below)

The owner clarified that the project must read **24 thermocouples**. A prior
proposal was to split acquisition over multiple boards communicating with a
master. That proposal was not recorded as a complete implemented architecture.
The current `hardware/8ch/` and firmware implement one eight-channel unit.

The owner subsequently said boards would be in the same panel, or not far
apart. More distant placement is a possible option to consider, not an
approved installation requirement. The owner will ask whether all 24 sensors
protect one machine with common shutdown, or separate machines/groups.
Do not infer three machines, three sensors per cylinder, or independent
shutdown merely from the number 24.

## Decision

Record 24 as the system requirement in AGENTS/GOAL/STATE. Retain the eight-channel
board as existing work and a candidate module. Do not change its channel-count
constant, regenerate hardware, remove RS-485, or order multiple boards on the
assumption that they already form a working system.

An accepted networked design requires addressing, a register/data contract,
reading validity/age, timeouts, startup/recovery, configuration ownership,
acknowledgement and output-fault behavior. RS-485 hardware is present but UART/
Modbus/master firmware is not implemented. The old protocol deferral cannot
be used to call the proposed networked 24-channel system complete.

## Original alternatives (selection recorded below)

1. One 24-channel PCB, initially assess four layers: fewer inter-board wires
   and duplicated support circuits; larger replaceable unit and a new layout.
   Independent shutdown groups require enough physical outputs from the outset.
2. Three eight-channel modules with a supervisory master: reuse a repeatable
   module, easier replacement and optional distributed placement, but extra
   supplies/controllers/interconnects and network software. A master may be a
   role on one module rather than automatically a fourth PCB; resources and
   failure behavior must be checked before choosing that arrangement.
3. Acquisition daughtercards and a common controller/backplane: potentially
   reduces duplicated electronics, but adds connector/backplane design and a
   common failure point. Not a reason to introduce a new subsystem by default.

For the modular option, prefer evaluating local autonomous trips and a
supervisor for display/configuration. Common versus independent machine
permission would then be an explicitly engineered wiring/output arrangement.
Putting contacts in series does **not** cure I-081's welded-contact/shorted-driver
failure limitation and is not a claimed safety solution.

## Rejected assumptions and consequences

* “Only a small software setting”: false if the required independent outputs,
  physical links or power/environment provisions are absent. Mapping can be
  configurable once supported by the chosen hardware and fault model.
* “24 channels needs five layers”: channel count alone does not determine
  layer count. Extra copper layers do not shrink connectors or components.
* “A simulator/MCP proves the board is safe”: tool control and model coverage
  are different; physical power/noise/thermal/assembly tests remain necessary.
* No final area or cost is claimed without a placement study and comparable
  quotes covering fabrication, assembly, parts, wiring and shipping.

Before architecture selection: confirm machine/channel grouping, independent
output count and loads, setpoint grouping, maximum node distance/environment,
display needs and enclosure limits. Existing 8-channel review findings remain
valid but do not qualify a 24-channel system. See I-085/I-086.

## Update 2026-10-01 — direction agreed with the owner

**Three identical, autonomous 8-channel modules**, each one the REV A2 board,
in one panel or nearby. Each module trips its own relay from its own readings.
This is alternative 2 without a master in the protection path.

* **One machine:** the three run-permit contacts are wired in series, so any
  module trips the machine.
* **Separate groups:** one contact per machine.
* Either way the module is the same board, so the grouping question no longer
  blocks ordering it. It decides the panel wiring (I-085).
* **A master later**, for one display, remote setpoints and logging, is mainly
  firmware (I-086). RS-485 (ADM2587E) is already on every module. It still
  needs a device to be the master (a PC, HMI, PLC or one module) and the bus
  wiring. It must never be able to grant RUN: losing communications must leave
  local protection untouched.

Why this over one 24-channel board: it reuses a board that is already reviewed;
one failed module takes out 8 channels, not 24; and there is no new layout,
bring-up or firmware resource study. Its cost is three supplies, three MCUs and
the wiring between modules, judged simpler than a new design (not yet costed).

Still true, as recorded above: contacts in series do not cure I-081 (a welded
contact or shorted driver). That is an accepted, documented limit (owner).

## Update 2026-10-07 — common shutdown confirmed

The owner confirmed **three independent eight-channel modules**, with their
**run-permit relay contacts in series**. A temperature trip or detected sensor
fault on any of the 24 channels opens the common machine-permission circuit.
The series connection is between relay contacts, not thermocouple inputs.
Separate shutdown groups are not selected for this installation.

Communication may be added later between modules, to an external master, or
with one module acting as master after checking its resources. It is optional
and must not bypass any module's autonomous protection. No master or protocol
is implemented by this clarification.

I-085 stays open for the installation wiring drawing and physical sensor mapping.
Per-channel setpoints are selected in `0029`, with implementation tracked as
I-100; common versus independent shutdown is answered. A common shutdown does
not prove equal probe ground potentials.
The accepted I-081 contact/driver failure limitation remains.
