"""Turn the passive requirements into orderable part numbers (I-007).

The schematic carries what each passive has to BE - value, tolerance,
dielectric, voltage - but not what to buy. An assembly house cannot take a BOM
that says "100n X7R"; it needs a manufacturer part number.

This script holds the requirement for every distinct passive on the board, asks
LCSC what satisfies it, and writes `passives_catalog.json`. Re-run it to refresh
stock and price. It is deliberately a separate step from the schematic: sourcing
data goes stale on its own schedule and should not force a schematic edit.

    python source_passives.py            # query and rewrite the catalog
    python source_passives.py --check    # verify the catalog covers every
                                         # requirement, no network

Selection rules, in order:
  1. the electrical requirement must be met - never traded away
  2. prefer a JLCPCB "basic" part (no extra assembly setup fee)
  3. prefer more stock
  4. prefer lower unit price

Rule 1 is absolute. If nothing meets the requirement the entry is left
unresolved and the script says so rather than substituting something close.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://jlcsearch.tscircuit.com"
CATALOG = Path(__file__).parent / "passives_catalog.json"
USER_AGENT = "thermo-8ch-sourcing/1.0"

R0805 = "Resistor_SMD:R_0805_2012Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1210 = "Capacitor_SMD:C_1210_3225Metric"

# Every distinct passive on the board, keyed by the Value string the schematic
# uses. `need` is the electrical requirement; anything not listed is free.
#
#   tol    maximum tolerance as a fraction (0.01 = 1%)
#   volt   minimum voltage rating
#   power  minimum power rating in watts
#   dielectric  exact temperature coefficient required
REQUIREMENTS = {
    # --- resistors ---------------------------------------------------------
    "0R":        dict(kind="r", footprint=R0805, ohms=0),
    "22R":       dict(kind="r", footprint=R0805, ohms=22, tol=0.05),
    "33R":       dict(kind="r", footprint=R0805, ohms=33, tol=0.05),
    "100R":      dict(kind="r", footprint=R0805, ohms=100, tol=0.05),
    # The eight matched pairs in the thermocouple front end.  Tolerance here is
    # not a preference: mismatch between the two legs turns common-mode noise
    # into differential noise, which is what destroys a microvolt measurement.
    "100R 0.1%": dict(kind="r", footprint=R0805, ohms=100, tol=0.001,
                      critical="TC input filter matched pair - CMRR depends "
                               "on the two legs being equal"),
    "120R 1%":   dict(kind="r", footprint=R0805, ohms=120, tol=0.01,
                      critical="RS-485 end-of-line termination"),
    "220R":      dict(kind="r", footprint=R0805, ohms=220, tol=0.05),
    "680R 1%":   dict(kind="r", footprint=R0805, ohms=680, tol=0.01),
    "4.7k 0.25W": dict(kind="r", footprint=R0805, ohms=4700, tol=0.05,
                       power=0.25),
    "10k":       dict(kind="r", footprint=R0805, ohms=10000, tol=0.05),
    # --- REV A1 (docs/decisions/0014) -------------------------------
    "22k":          dict(kind="r", footprint=R0805, ohms=22e3,
                         critical="run-permit read-back divider, upper leg;\n                                   with R54 it puts ~4.2 V on PC2 from 24 V"),
    "4k7":          dict(kind="r", footprint=R0805, ohms=4.7e3,
                         critical="run-permit read-back divider, lower leg"),
    "100k":      dict(kind="r", footprint=R0805, ohms=100000, tol=0.05),

    # --- LM5164 input stage (decisions/0016, CALCULATIONS.md 1) -------------
    # All 1 %: these five set the switching frequency, the output voltage and
    # the under-voltage lockout.  A 5 % part here moves the 5 V rail.
    "41.2k 1%":  dict(kind="r", footprint=R0805, ohms=41.2e3, tol=0.01,
                      critical="LM5164 on-time resistor - sets 303 kHz"),
    "158k 1%":   dict(kind="r", footprint=R0805, ohms=158e3, tol=0.01,
                      critical="feedback divider upper - directly sets the 5 V rail"),
    "49.9k 1%":  dict(kind="r", footprint=R0805, ohms=49.9e3, tol=0.01,
                      critical="feedback divider lower - directly sets the 5 V rail"),
    "150k 1%":   dict(kind="r", footprint=R0805, ohms=150e3, tol=0.01,
                      critical="Type-3 ripple injection - too large and the "
                               "converter loses the ripple it needs to stay stable"),
    "33.2k 1%":  dict(kind="r", footprint=R0805, ohms=33.2e3, tol=0.01,
                      critical="EN/UVLO divider upper - sets the 6.48 V release"),
    "10k 1%":    dict(kind="r", footprint=R0805, ohms=10e3, tol=0.01,
                      critical="EN/UVLO divider lower"),

    # --- capacitors --------------------------------------------------------
    # C0G/NP0 in the signal path: X7R's voltage and temperature coefficients
    # would modulate the filter these caps define.
    # The schematic asks for C0G here and NO SUCH PART EXISTS in 0805 - the
    # dielectric's permittivity is too low to reach 100 nF in that size.  It
    # starts at 1206, which the frozen board has no footprint for.  X7R is
    # accepted instead and the schematic Value now says so.
    # docs/decisions/0011 has the reasoning; I-035 is closed.
    "100n X7R 50V": dict(kind="c", footprint=C0805, farads=100e-9,
                         volt=50, dielectric="X7R", tol=0.1,
                         critical="TC differential filter - dielectric stability is "
                                  "part of the measurement",
                         substitution="Was specified C0G until 2026-09-08: 100 nF C0G "
                                      "does not exist in 0805 (0 in stock, any "
                                      "maker; available from 1206 up, which "
                                      "the frozen REV A0 board cannot take).  "
                                      "Acceptable here because the capacitor "
                                      "sits across T+/T- with essentially no "
                                      "DC bias, so X7R's voltage coefficient "
                                      "does not apply, and the unit is in a "
                                      "panel 50 m from the engine, so X7R's "
                                      "piezoelectric response has nothing to "
                                      "excite it (docs/decisions/0009)."),
    "10n C0G 50V":  dict(kind="c", footprint=C0805, farads=10e-9,
                         volt=50, dielectric="C0G",
                         critical="TC common-mode filter"),
    # --- REV A1 (docs/decisions/0014) -------------------------------
    "22p C0G 50V":  dict(kind="c", footprint=C0805, farads=22e-12,
                         volt=50, dielectric="C0G",
                         critical="Y1 crystal load capacitor - the load\n                                   capacitance sets the oscillator\n                                   frequency, so C0G is not optional here"),
    "100n X7R":     dict(kind="c", footprint=C0805, farads=100e-9, volt=16,
                         dielectric="X7R"),
    "10n X7R":      dict(kind="c", footprint=C0805, farads=10e-9, volt=16,
                         dielectric="X7R"),
    "1u X7R":       dict(kind="c", footprint=C0805, farads=1e-6, volt=16,
                         dielectric="X7R"),
    # C48, the LP2985-3.3 output bypass feeding eight MAX31856 and two
    # isolators.  The generator has said 4.7 uF since f60e6d3 while the
    # schematic still said 1 uF - the drift was only found on 2026-09-08 when
    # --refresh-properties was finally run.  See I-044.
    "4.7u X7R 16V": dict(kind="c", footprint=C0805, farads=4.7e-6, volt=16,
                         dielectric="X7R",
                         critical="LDO output bulk for the whole sensor "
                                  "island"),
    "2.2u 50V X7R": dict(kind="c", footprint=C0805, farads=2.2e-6, volt=50,
                         dielectric="X7R"),
    "10u 10V":      dict(kind="c", footprint=C0805, farads=10e-6, volt=10),
    "10u 10V X7R":  dict(kind="c", footprint=C0805, farads=10e-6, volt=10,
                         dielectric="X7R"),
    "10u X7R":      dict(kind="c", footprint=C0805, farads=10e-6, volt=16,
                         dielectric="X7R"),
    # --- LM5164 input stage (decisions/0016) --------------------------------
    # 100 V parts because the supply is a battery: a suppressed load dump sits
    # at 58 V for ~350 ms and a 50 V capacitor does not survive that.
    "4.7u 100V X7R": dict(kind="c", footprint=C1210, farads=4.7e-6, volt=100,
                          dielectric="X7R",
                          critical="buck input bypass - TI asks for 2 x the max "
                                   "input voltage because of ceramic DC bias loss"),
    "22u 25V X7R":   dict(kind="c", footprint=C1210, farads=22e-6, volt=25,
                          dielectric="X7R",
                          critical="buck output capacitor"),
    "2.2n 50V X7R":  dict(kind="c", footprint=C0805, farads=2.2e-9, volt=50,
                          dielectric="X7R",
                          critical="bootstrap - the datasheet fixes this at 2.2 nF, "
                                   "1.5-2.5 nF absolute"),
    "3.3n 50V X7R":  dict(kind="c", footprint=C0805, farads=3.3e-9, volt=50,
                          dielectric="X7R",
                          critical="Type-3 ripple injection"),
    "220p C0G 50V":  dict(kind="c", footprint=C0805, farads=220e-12, volt=50,
                          dielectric="C0G",
                          critical="ripple coupling into FB - C0G because the part "
                                   "must not lose value under DC bias"),
}

# Parts the LCSC parametric search does not cover.  Specified by hand, with the
# reason, so they are not silently missing from the catalog.
MANUAL = {
    "47u 50V": dict(
        footprint="Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
        mpn="EEUFR1H470", manufacturer="Panasonic",
        note="Through-hole radial electrolytic, 47uF 50V, 6.3 mm, 105 degC, "
             "low ESR. The parametric search covers surface-mount parts; this "
             "is the 24 V bulk reservoir and is fitted by hand.",
    ),
    "22u 100V": dict(
        footprint="Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
        mpn="EEUFC2A220", manufacturer="Panasonic",
        note="Through-hole radial electrolytic, 22uF 100V, 8 mm, 105 degC. "
             "Replaces the 47uF 50V part: the supply is a battery and 50 V does "
             "not survive a 58 V load dump. The value dropped because this "
             "capacitor was never ride-through - 47uF buys 5.7 ms (CALCULATIONS.md "
             "section 2). Its job now is bulk and parallel damping for the 50 m "
             "feed, which 22uF does.",
    ),
    "10k LCD CONTRAST": dict(
        footprint="Potentiometer_Bourns_3296W_Vertical",
        mpn="3296W-1-103LF", manufacturer="Bourns",
        note="25-turn cermet trimmer, 10k. Set once at commissioning for LCD "
             "contrast; not a parametric search candidate.",
    ),
}


def fetch(path: str, params: dict) -> list[dict]:
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}&json=true"
    # The service rejects urllib's default User-Agent with a 403.
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SystemExit(f"query failed for {url}\n  {error}")


def meets(part: dict, need: dict) -> bool:
    tol = need.get("tol")
    if tol is not None:
        actual = part.get("tolerance_fraction")
        if actual is None or actual > tol + 1e-12:
            return False
    volt = need.get("volt")
    if volt is not None:
        actual = part.get("voltage_rating")
        if actual is None or actual < volt:
            return False
    power = need.get("power")
    if power is not None:
        actual = part.get("power_watts")
        # The API reports milliwatts in a field named watts for some parts.
        if actual is None:
            return False
        watts = actual / 1000.0 if actual > 10 else actual
        if watts < power - 1e-12:
            return False
    dielectric = need.get("dielectric")
    if dielectric is not None:
        actual = (part.get("temperature_coefficient") or "").upper()
        # NP0 and C0G are the same specification under two names.
        wanted = {"C0G", "NP0"} if dielectric.upper() in ("C0G", "NP0") \
            else {dielectric.upper()}
        if actual not in wanted:
            return False
    return bool(part.get("in_stock"))


def rank(part: dict) -> tuple:
    return (0 if part.get("is_basic") else 1,
            -(part.get("stock") or 0),
            part.get("price1") or 9e9)


def package_of(footprint: str) -> str:
    """Imperial package code out of a KiCad footprint name.

    This used to be hardcoded to "0805", which silently made every non-0805
    requirement unresolvable: the search asked for a 0805 part, found nothing
    that also met the voltage rating, and reported "nothing in stock meets the
    requirement" - which was not true. The LM5164 input stage needs 1210 for
    its 100 V and 22 uF parts.
    """
    for code in ("0402", "0603", "0805", "1206", "1210", "1812", "2220"):
        if code in footprint:
            return code
    return "0805"


def resolve(value: str, need: dict) -> dict | None:
    package = package_of(need.get("footprint", ""))
    if need["kind"] == "r":
        candidates = fetch("resistors/list",
                           {"resistance": need["ohms"], "package": package})
        candidates = candidates.get("resistors", [])
    else:
        candidates = fetch("capacitors/list",
                           {"capacitance": need["farads"], "package": package})
        candidates = candidates.get("capacitors", [])

    usable = [p for p in candidates if meets(p, need)]
    if not usable:
        return None
    best = sorted(usable, key=rank)[0]
    return {
        "mpn": best["mfr"],
        "lcsc": f"C{best['lcsc']}",
        "footprint": need["footprint"],
        "jlcpcb_basic": bool(best.get("is_basic")),
        "stock": best.get("stock"),
        "unit_price_usd": round(best.get("price1") or 0, 6),
        "measured": {
            "tolerance_fraction": best.get("tolerance_fraction"),
            "voltage_rating": best.get("voltage_rating"),
            "temperature_coefficient": best.get("temperature_coefficient"),
            "power_watts": best.get("power_watts"),
        },
        "alternates": [
            {"mpn": p["mfr"], "lcsc": f"C{p['lcsc']}"}
            for p in sorted(usable, key=rank)[1:3]
        ],
    }


def check() -> int:
    if not CATALOG.exists():
        print(f"FAIL  {CATALOG.name} does not exist - run without --check")
        return 1
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["parts"]
    missing = [v for v in list(REQUIREMENTS) + list(MANUAL)
               if v not in catalog or not catalog[v].get("mpn")]
    if missing:
        print(f"FAIL  {len(missing)} requirement(s) with no part number:")
        for value in missing:
            print(f"        {value}")
        return 1
    print(f"ok    {len(catalog)} passive types, every one has an MPN")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()

    parts: dict[str, dict] = {}
    unresolved: list[str] = []

    for value, need in REQUIREMENTS.items():
        found = resolve(value, need)
        if found is None:
            unresolved.append(value)
            print(f"UNRESOLVED  {value}  - nothing in stock meets the "
                  f"requirement")
            continue
        if "critical" in need:
            found["why_it_matters"] = need["critical"]
        if "substitution" in need:
            found["substitution"] = need["substitution"]
        parts[value] = found
        basic = "basic" if found["jlcpcb_basic"] else "extended"
        print(f"ok  {value:<14} {found['mpn']:<22} {found['lcsc']:<9} "
              f"{basic:<8} stock {found['stock']:>9,}")

    for value, entry in MANUAL.items():
        parts[value] = dict(entry, jlcpcb_basic=False, sourced="manual")
        print(f"ok  {value:<14} {entry['mpn']:<22} {'(manual)':<9}")

    CATALOG.write_text(json.dumps({
        "note": "Generated by source_passives.py. Stock and price are a "
                "snapshot; re-run before ordering. The electrical requirement "
                "is in the script, not here.",
        "unresolved": unresolved,
        "parts": parts,
    }, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\n{len(parts)} resolved, {len(unresolved)} unresolved "
          f"-> {CATALOG.name}")
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
