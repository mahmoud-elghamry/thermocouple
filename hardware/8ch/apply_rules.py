"""Write the board's design rules into the KiCad project itself.

Track widths, via sizes and clearances used to live as constants inside the
placement/routing script, which meant nobody opening the project in KiCad could
see or check them.  They belong to the project:

  * ``thermocouple_8ch.kicad_pro``  -> net classes and net-class patterns
  * ``thermocouple_8ch.kicad_dru``  -> custom clearance rules (isolation,
    relay contacts, chassis/PE)

Run this before generating the board.  It is idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRO = ROOT / "thermocouple_8ch.kicad_pro"
DRU = ROOT / "thermocouple_8ch.kicad_dru"


# --------------------------------------------------------------------------
# Net classes
# --------------------------------------------------------------------------
# ``clearance`` here is the class' own minimum.  Clearance *between* domains is
# enforced by the custom rules in the .kicad_dru file, because that is a
# property of the pair, not of one class.

CLASSES: list[dict] = [
    # name              track  clear  via_d via_dr  patterns
    dict(name="Default", track_width=0.25, clearance=0.20,
         via_diameter=0.60, via_drill=0.30, patterns=[]),

    dict(name="SensorSignal", track_width=0.25, clearance=0.25,
         via_diameter=0.60, via_drill=0.30,
         patterns=["/TC?_RAW_?", "/TC?_FILT_?", "/MISO_CH?",
                   "/CS?_SENS", "/CS?_SENS_RAW",
                   "/SCK_SENS", "/SCK_SENS_RAW",
                   "/MOSI_SENS", "/MOSI_SENS_RAW",
                   "/MISO_SENS", "/MISO_SENS_RAW",
                   "/ISO_SPARE_SENS"]),

    dict(name="SensorPower", track_width=0.60, clearance=0.25,
         via_diameter=0.80, via_drill=0.40,
         patterns=["/+3V3_SENS", "/GND_SENS", "/+5V_ISO", "/NEG5_UNUSED"]),

    dict(name="CtrlPower", track_width=0.60, clearance=0.20,
         via_diameter=0.80, via_drill=0.40,
         patterns=["/+5V_CTRL", "/GND_CTRL"]),

    # 24 V rail: 0.5 A PTC, so ~0.5 A worst case.  0.8 mm on 1 oz outer copper
    # is far above the thermal need; the width is chosen for mechanical
    # robustness and low impedance on the relay coil path.  Clearance is 0.25
    # mm because the 2N7000's TO-92 inline footprint puts RELAY_LOW 1.27 mm
    # from RELAY_GATE - the package sets this limit, and 0.25 mm is still far
    # beyond what 24 V needs.
    dict(name="Power24V", track_width=0.80, clearance=0.25,
         via_diameter=0.90, via_drill=0.50,
         patterns=["/+24V_RAW", "/+24V_FUSED", "/+24V_PROT",
                   "/RELAY_LOW", "/RELAY_LED_A"]),

    # Dry contact brought out on J3.  Marked LOW-VOLTAGE LOAD ONLY on the
    # silkscreen; this margin is functional, NOT a mains-rated creepage
    # qualification.  Kept equal to RELAY_CLEARANCE_MM so the autorouter and
    # the DRC work to the same number.
    dict(name="RelayContact", track_width=1.20, clearance=2.00,
         via_diameter=1.00, via_drill=0.60,
         patterns=["/RELAY_COM", "/RELAY_NO", "/RELAY_NC"]),

    dict(name="RS485", track_width=0.40, clearance=0.25,
         via_diameter=0.70, via_drill=0.35,
         patterns=["/RS485_A", "/RS485_B", "/RS485_TERM_A",
                   "/RS485_BIAS_A", "/RS485_BIAS_B",
                   "/+5V_RS485", "/GND_RS485"]),

    # Cable-shield / PE ring.  Deliberately isolated from all three signal
    # grounds; bonded to the four M3 mounting holes and to J1.3 / J4.4.
    # The class clearance matches CHASSIS_CLEARANCE_MM below so the autorouter
    # and the DRC agree; a mismatch just produces violations the router had no
    # way to avoid.
    dict(name="Chassis", track_width=0.80, clearance=1.50,
         via_diameter=0.80, via_drill=0.40,
         patterns=["/CHASSIS_SHIELD"]),

    # Pins that carry no net: XTAL1/XTAL2, LCD D0-D3, the MAX31856 DNC/DRDY/
    # FAULT pins, and so on.  KiCad still gives each one a placeholder net, and
    # without this class those placeholders land in Default and get dragged
    # into the isolation rules below - which produced 445 clearance "errors"
    # against pads that are not electrically connected to anything at all.
    dict(name="NoConnect", track_width=0.25, clearance=0.20,
         via_diameter=0.60, via_drill=0.30,
         patterns=["unconnected-*"]),
]

# Which classes belong to which galvanically separated island.
SENSOR_ISLAND = ("SensorSignal", "SensorPower")
CONTROL_ISLAND = ("Default", "CtrlPower", "Power24V")
RS485_ISLAND = ("RS485",)

# Minimum copper-to-copper spacing between two islands, in mm.
#
# This is FUNCTIONAL isolation for an engineering prototype.  The limit is set
# by the parts themselves, not by a safety standard: the tightest crossing on
# the board is the IA0505S module, whose 5.08 mm pin pitch leaves a 3.23 mm pad
# gap between -Vin (control) and -Vout (sensor).  Every other crossing
# (ISO7760/ISO7761/ADM2587E, SOIC-W packages) leaves 7.25 mm.  Certifying this
# as a safety barrier needs creepage/clearance analysis against IEC 61010 with
# the real working voltage and pollution degree, which has not been done.
ISLAND_CLEARANCE_MM = 3.0

# Relay dry contact and chassis/PE to anything else.
# The dry contact will switch a real load on a machine.  2.0 mm is the most
# the layout can guarantee: the MKDS-1,5-3 terminal itself puts its screws on a
# 5.00 mm pitch, which leaves 2.4 mm of copper between adjacent contact pads,
# so nothing on this board can hold more than that at J3.  Phoenix rates that
# terminal to 320 V; the board is still marked LOW-VOLTAGE LOAD ONLY because
# the rest of the layout has not been qualified to a mains standard.
RELAY_CLEARANCE_MM = 2.0
CHASSIS_CLEARANCE_MM = 1.5


def _class_entry(spec: dict) -> dict:
    """Fill a KiCad net-class record, keeping every key KiCad expects."""
    return {
        "bus_width": 12,
        "clearance": spec["clearance"],
        "diff_pair_gap": 0.25,
        "diff_pair_via_gap": 0.25,
        "diff_pair_width": 0.2,
        "line_style": 0,
        "microvia_diameter": 0.3,
        "microvia_drill": 0.1,
        "name": spec["name"],
        "pcb_color": "rgba(0, 0, 0, 0.000)",
        "priority": 2147483647 if spec["name"] == "Default" else CLASSES.index(spec),
        "schematic_color": "rgba(0, 0, 0, 0.000)",
        "track_width": spec["track_width"],
        "tuning_profile": "",
        "via_diameter": spec["via_diameter"],
        "via_drill": spec["via_drill"],
        "wire_width": 6,
    }


def update_project() -> None:
    project = json.loads(PRO.read_text(encoding="utf-8"))

    net_settings = project.setdefault("net_settings", {})
    net_settings["classes"] = [_class_entry(spec) for spec in CLASSES]
    net_settings["netclass_patterns"] = [
        {"netclass": spec["name"], "pattern": pattern}
        for spec in CLASSES for pattern in spec["patterns"]
    ]
    net_settings.setdefault("meta", {"version": 5})

    design = project["board"]["design_settings"]

    # P-02 in the design review: a DRC pass with the courtyard check switched
    # off is not a DRC pass.  A mechanical collision is worse than a clearance
    # violation because it only shows up after the boards are built.
    severities = design["rule_severities"]
    severities["missing_courtyard"] = "error"
    severities["courtyards_overlap"] = "error"
    severities["malformed_courtyard"] = "error"

    rules = design["rules"]
    rules["min_clearance"] = 0.2
    rules["min_track_width"] = 0.2
    rules["min_via_diameter"] = 0.5
    rules["min_through_hole_diameter"] = 0.3
    rules["min_copper_edge_clearance"] = 0.5
    rules["min_hole_clearance"] = 0.25
    rules["min_hole_to_hole"] = 0.25

    design["track_widths"] = [0.0, 0.25, 0.40, 0.60, 0.80, 1.20]
    design["via_dimensions"] = [
        {"diameter": 0.0, "drill": 0.0},
        {"diameter": 0.60, "drill": 0.30},
        {"diameter": 0.80, "drill": 0.40},
        {"diameter": 0.90, "drill": 0.50},
        {"diameter": 1.00, "drill": 0.60},
    ]

    PRO.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {PRO.name}: {len(CLASSES)} net classes, "
          f"{len(net_settings['netclass_patterns'])} patterns")


def _class_test(side: str, names: tuple[str, ...]) -> str:
    return "(" + " || ".join(f"{side}.NetClass == '{n}'" for n in names) + ")"


def _pair_condition(left: tuple[str, ...], right: tuple[str, ...]) -> str:
    """Symmetric condition so the rule fires regardless of A/B ordering."""
    return (f"({_class_test('A', left)} && {_class_test('B', right)}) || "
            f"({_class_test('A', right)} && {_class_test('B', left)})")


def write_dru() -> None:
    lines = [
        "(version 1)",
        "",
        "# Custom design rules for the 8-channel thermocouple protection board.",
        "# Generated by apply_rules.py - edit that file, not this one.",
        "#",
        "# The board carries three separately referenced copper islands:",
        "#   sensor island   fed by U12 (IA0505S) + U13, referenced to GND_SENS",
        "#   control island  fed by U14 from +24 V,      referenced to GND_CTRL",
        "#   RS-485 island   fed by the ADM2587E,        referenced to GND_RS485",
        "# Signals cross only through U10/U11 (ISO7760/ISO7761) and U15.",
        "#",
        "# These are FUNCTIONAL isolation rules for an engineering prototype.",
        "# They are not a safety-barrier qualification: no creepage/clearance",
        "# analysis against IEC 61010 has been performed, and the shared sensor",
        "# island still leaves the eight thermocouples common to each other.",
        "",
    ]

    for label, left, right in (
        ("sensor_to_control", SENSOR_ISLAND, CONTROL_ISLAND),
        ("sensor_to_rs485", SENSOR_ISLAND, RS485_ISLAND),
        ("control_to_rs485", CONTROL_ISLAND, RS485_ISLAND),
    ):
        lines += [
            f'(rule "isolation_{label}"',
            f'  (constraint clearance (min {ISLAND_CLEARANCE_MM}mm))',
            f'  (condition "{_pair_condition(left, right)}"))',
            "",
        ]

    others = tuple(n for n in (s["name"] for s in CLASSES) if n != "RelayContact")
    lines += [
        '# Dry contact on J3.  Marked LOW-VOLTAGE LOAD ONLY; this margin is',
        '# functional, not a mains creepage qualification.',
        '(rule "relay_contact_to_everything_else"',
        f'  (constraint clearance (min {RELAY_CLEARANCE_MM}mm))',
        f'  (condition "{_pair_condition(("RelayContact",), others)}"))',
        "",
    ]

    others = tuple(n for n in (s["name"] for s in CLASSES) if n != "Chassis")
    lines += [
        '# Cable-shield / PE ring: isolated from all three signal grounds so a',
        '# shield current cannot become a measurement ground loop.',
        '(rule "chassis_to_everything_else"',
        f'  (constraint clearance (min {CHASSIS_CLEARANCE_MM}mm))',
        f'  (condition "{_pair_condition(("Chassis",), others)}"))',
        "",
        '# Thermocouple inputs measure microvolts; keep the annular ring healthy',
        '# on the few vias they are allowed to use.',
        '(rule "sensor_signal_annular_ring"',
        '  (constraint annular_width (min 0.15mm))',
        '  (condition "A.NetClass == \'SensorSignal\'"))',
        "",
    ]

    DRU.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {DRU.name}: 5 custom rules")


if __name__ == "__main__":
    update_project()
    write_dru()
