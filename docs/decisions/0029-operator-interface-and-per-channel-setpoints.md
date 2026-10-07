# 0029 — Operator requirements: dry contact and per-channel setpoints

* Status: accepted requirements; implementation and rating choices pending
* Date: 2026-10-07
* Decider: owner, reporting the operations engineer's answers
* Relates to: `0024`, `0028`, `0016`, I-085/I-089/I-091/I-092/I-093/I-100

## Confirmed requirements

* **Three autonomous eight-channel modules**, with run-permit contacts in
  series for common shutdown (`0024`). A master/communications may come later.
* **Potential-free dry contact:** the machine installer provides the switched
  voltage; the PCB must not inject its own supply into the contact terminals.
  The operator wants flexibility to switch a positive line, negative line,
  24 V or another external circuit, mentioning "line" without a voltage.
* **One operator-adjustable trip setpoint per channel**, retained across power
  cycles. The operator selects actual temperature limits during commissioning;
  do not require a single common setpoint per eight-channel module or hard-code
  the operating trip temperatures. Any channel trip still opens that module's
  relay and hence the common series circuit.
* **Manual ACK confirmed.** Retain the existing startup/reset/trip latch policy:
  no automatic restart; ACK only permits running once all required channels
  have valid readings and meet their own reset-temperature conditions.
* The owner accepts the existing **K-type shielded twisted extension-cable
  basis, roughly 50 m**. This is not an exact cable manufacturer/part number,
  wire gauge, routing or shield-termination specification.
* The probes are **probably grounded-junction**, according to the owner;
  that is not established by a part number, datasheet or continuity measurement.
* **Display type, mounting and button arrangement are design-team decisions.**
  The LCD sits off the main PCB. Select a practical local interface for three
  modules; any later shared display/master must leave local trips autonomous.
* **Supply is already specified: engine battery, nominal 24 VDC (`0016`).**
  Reuse that requirement; transient/cranking qualification remains engineering
  work, not a new request to choose the source.

## Limits and implementation work

**Dry contact does not mean unlimited voltage/current.** Existing REV A2 is
explicitly LOW-VOLTAGE LOAD ONLY. A relay's component mains rating does not
qualify the PCB clearance, connector, fuse, enclosure or the complete product.
If "line" means mains, that capability requires a separately reviewed rated
interface/redesign. Do not silently approve it. Define the final low-voltage
contact envelope and minimum reliable load in I-092; a suitably rated external
interposing relay is an option for loads outside it, not a selected part.

**Per-channel setpoints are not implemented yet (I-100).** Current settings,
protection and UI use one scalar setpoint per module. Plan channel selection,
eight validated limits, CRC-protected persistence, explicit old-record migration
or configuration lock, failed-save behavior, per-channel trip/ACK/hysteresis,
and tests before changing firmware. Verify memory/resources before any MCU change.

Adjustable limits do not remove the need to define a valid sensor/probe range,
plausibility thresholds and allowed UI range. Actual trip numbers belong to
commissioning; do not invent them from the converter's maximum range.

**Electrical isolation of the measuring junction from the sheath does not
prevent temperature measurement.** Heat still reaches the junction through
the insulating material; grounded/ungrounded describe an electrical connection,
not whether the probe senses heat. Keep the existing shared-island acceptance
(`0009`); verify actual grounding and potential differences (I-004/I-026).

## Datasheet evidence

`docs/reference/datasheets/MAX31856.pdf` already exists and was opened in this
session. It describes the reader IC, not the actual physical probe. The probe
manufacturer/model is absent from the reviewed source documents, so its exact
datasheet cannot be identified honestly. Obtain it when the physical part is
identified; do not label a generic K-type catalog as the installed probe's sheet.
Attempted manufacturer references (Analog Devices/Omega) returned HTTP 403 in
this cloud. Existing MAX31856 documentation remains available offline.

## Rejected alternatives and consequences

* One shared trip threshold per module: replaced by independent channel limits.
* Treating "free contact" as permission to connect any circuit: rejected;
  contact and complete-interface ratings are still required.
* Treating a likely grounded probe as verified, or saying an ungrounded probe
  cannot measure: rejected; model/measurement establishes the electrical type.
* Asking operations to choose the display or battery/panel supply again:
  unnecessary; interface selection is delegated and battery supply is recorded.

This change records requirements and handoff only. It implements no firmware,
hardware substitution, A3 layout, contact rating or procurement order.
