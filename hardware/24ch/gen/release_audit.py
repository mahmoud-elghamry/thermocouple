"""Release audit beyond DRC (I-133): family holes.py and pourcheck.py on the refilled release snapshot.

Runs in KiCad's python:  python.exe release_audit.py <release folder>
Writes HOLES-POUR.txt. Fails on: any hole pair closer than 0.25 mm, any via near a land of another net,
any via near a land that is not in release_text.VIAS_NEAR_PADS (the disclosed list), any pad or via not
reachable from its pour. The family audit functions are imported directly (no board profile needed).
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "family", "tools"))
import holes          # noqa: E402  (family/tools)
import pourcheck      # noqa: E402
from release_text import VIAS_NEAR_PADS  # noqa: E402


def main(rel):
    pcb = os.path.join(rel, "source-snapshot", "thermo24.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    h = holes.audit(board)
    pr = pourcheck.audit(board)
    bad, lines = [], [f"HOLES AND POUR AUDIT - {os.path.basename(rel.rstrip(chr(92) + '/'))}",
                      f"board: source-snapshot/thermo24.kicad_pcb (refilled by DRC); KiCad {pcbnew.GetBuildVersion()}",
                      f"holes {h['holes']}, vias {h['vias']}, SMD lands {h['smd_lands']}; "
                      f"exempt heatsink pads {', '.join(x['pad'] for x in h['exempt_heatsinks'])}",
                      f"hole pairs closer than {h['hole_clearance_mm']} mm: {h['hole_pairs']}",
                      f"vias closer than {h['land_clearance_mm']} mm to an SMD land: {h['via_land_pairs']}"]
    if h["hole_pairs"]:
        bad.append(f"{h['hole_pairs']} hole pairs too close")
    for d in sorted(h["land_details"], key=lambda d: d["edge_gap_mm"]):
        pad, vnet, lnet = d["land"]["pad"], d["via"]["net"], d["land"]["net"]
        known = VIAS_NEAR_PADS.get(pad)
        verdict = "disclosed" if vnet == lnet and known and known[0] == vnet else "NOT ACCEPTED"
        lines.append(f"  {pad} ({lnet}) <- via {vnet}: holes.py edge gap {d['edge_gap_mm']:.3f} mm  {verdict}")
        if verdict != "disclosed":
            bad.append(f"via {vnet} at {pad} ({lnet})")
    lines.append(f"pour: {pr['zone_layers']} zone layers, {pr['inspected_items']} pads/vias on pour nets, "
                 f"{pr['reachable_fill']} reach their fill, {pr['unattached']} unattached, "
                 f"{len(pr['empty_zone_layers'])} empty zone layers")
    if pr["unattached"] or pr["empty_zone_layers"]:
        bad.append(f"pour: {pr['unattached']} unattached, {len(pr['empty_zone_layers'])} empty zone layers")
    lines.append("verdict: " + ("FAIL - " + "; ".join(bad) if bad else "PASS"))
    with open(os.path.join(rel, "HOLES-POUR.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
