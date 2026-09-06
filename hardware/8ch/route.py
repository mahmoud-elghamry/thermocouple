"""Route the board with Freerouting through Specctra DSN/SES.

The previous generator carried its own A* maze router.  It only moved along
X and Y, had no rip-up-and-retry, and modelled clearance as grid occupancy, so
it produced ~4000 track segments, 22 crossings, 304 clearance violations and
still left five nets unfinished.  Freerouting is an established open-source
autorouter with 45-degree routing, rip-up and retry, and a real clearance
model, and its output is ordinary KiCad track segments that can be edited by
hand afterwards.

Pipeline::

    pcbnew  ->  .dsn  ->  freerouting  ->  .ses  ->  pcbnew

Two edits are made to the exported DSN before handing it over:

1.  KiCad writes every copper layer as ``(type signal)``.  In1/In2 are power
    and ground planes here, and routing signals through them is what fragments
    the return path.  They are re-declared ``(type power)`` so Freerouting
    keeps signals on F.Cu and B.Cu only.
2.  Wiring that already exists on the board - the chassis/PE ring and the
    plane-stitching vias - is re-declared ``(type protect)`` so the optimiser
    does not rip it up.

Requires Freerouting and a JRE; see ``FREEROUTING_JAR`` / ``JAVA`` below or the
matching environment variables.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import pcbnew

import generate_board as gb


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
DSN = OUT / "thermocouple_8ch.dsn"
SES = OUT / "thermocouple_8ch.ses"
LOG = OUT / "freerouting.log"

TOOLS = Path(os.environ.get("KICAD_TOOLS_DIR",
                            Path.home() / "AppData/Local/kicad-tools"))
FREEROUTING_JAR = Path(os.environ.get("FREEROUTING_JAR",
                                      TOOLS / "freerouting.jar"))


def find_java() -> Path:
    override = os.environ.get("FREEROUTING_JAVA")
    if override:
        return Path(override)
    candidates = sorted((TOOLS / "jre25").glob("*/bin/java.exe"))
    if candidates:
        return candidates[0]
    raise SystemExit(
        "No Java 25 runtime found.  Freerouting 2.4.x needs class file "
        "version 69 (Java 25).  Set FREEROUTING_JAVA to a java executable, or "
        f"unpack a JRE under {TOOLS / 'jre25'}.")


# Nets whose existing wiring must survive optimisation.
# Wiring this project draws on purpose and does not want the optimiser to
# move: the chassis ring, and the fixed supply escapes on each channel.
PROTECTED_NETS = {"/CHASSIS_SHIELD", "/+3V3_SENS"}
PLANE_LAYERS = ("In1.Cu", "In2.Cu")


def export_dsn() -> None:
    OUT.mkdir(exist_ok=True)
    board = pcbnew.LoadBoard(str(gb.BOARD_FILE))
    if not pcbnew.ExportSpecctraDSN(board, str(DSN)):
        raise SystemExit("Specctra DSN export failed")

    text = DSN.read_text(encoding="utf-8", errors="replace")

    for layer in PLANE_LAYERS:
        pattern = re.compile(r"(\(layer\s+" + re.escape(layer)
                             + r"\s*\n\s*\(type\s+)signal(\s*\))")
        text, count = pattern.subn(r"\1power\2", text)
        if count != 1:
            raise SystemExit(f"Could not mark {layer} as a power layer "
                             f"({count} matches)")

    # Freerouting works to its own grid and lands a few microns inside the
    # number it was given (0.2454 mm against a 0.25 mm rule).  Hand it a
    # slightly larger clearance so its rounding still satisfies KiCad's DRC.
    def _pad_clearance(match: "re.Match[str]") -> str:
        return f"(clearance {int(match.group(1)) + 60})"

    text = re.sub(r"\(clearance (\d+)\)", _pad_clearance, text)

    protected = 0
    lines = []
    for line in text.splitlines(keepends=True):
        if "(type route)" in line and any(f"(net {net})" in line
                                          for net in PROTECTED_NETS):
            line = line.replace("(type route)", "(type protect)")
            protected += 1
        lines.append(line)
    DSN.write_text("".join(lines), encoding="utf-8")

    print(f"Exported {DSN.name}: In1/In2 marked as power planes, "
          f"{protected} chassis-ring segments protected")


def run_freerouting(passes: int, threads: int) -> None:
    java = find_java()
    if not FREEROUTING_JAR.exists():
        raise SystemExit(f"Freerouting jar not found: {FREEROUTING_JAR}")
    command = [str(java), "-jar", str(FREEROUTING_JAR),
               "-de", str(DSN), "-do", str(SES),
               "-mp", str(passes), "-mt", str(threads)]
    print("Running: " + " ".join(command), flush=True)
    with LOG.open("w", encoding="utf-8") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                text=True)
    tail = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]
    print("\n".join(tail))
    if result.returncode != 0:
        raise SystemExit(f"Freerouting exited with {result.returncode}; "
                         f"see {LOG}")
    if not SES.exists():
        raise SystemExit(f"Freerouting produced no session file; see {LOG}")


MIN_TRACK_MM = 0.20


def import_ses() -> None:
    board = pcbnew.LoadBoard(str(gb.BOARD_FILE))
    if not pcbnew.ImportSpecctraSES(board, str(SES)):
        raise SystemExit("Specctra SES import failed")

    # Do all reading before the first Remove(): once anything is removed from a
    # board, KiCad's SWIG bindings hand out bare pointers for the rest of the
    # process.
    tracks = list(board.GetTracks())
    chassis = [t for t in tracks
               if gb.bare(t.GetNetname()) == "CHASSIS_SHIELD"]

    # Freerouting emits a few segments just under the minimum width (0.1874 mm
    # against a 0.20 mm floor).  Widening them is safe and keeps DRC honest.
    narrow = 0
    for track in tracks:
        if track.Type() == pcbnew.PCB_VIA_T:
            continue
        if pcbnew.ToMM(track.GetWidth()) < MIN_TRACK_MM - 1e-6:
            track.SetWidth(pcbnew.FromMM(MIN_TRACK_MM))
            narrow += 1

    # The chassis/PE net is not the router's to design.  Freerouting ignores
    # the "protect" flag on it and produces a minimum-length tree across the
    # board instead of a ring, so whatever it drew is discarded and the ring is
    # redrawn deterministically.
    for track in chassis:
        try:
            board.Remove(track)
        except AttributeError:
            pass
    pcbnew.SaveBoard(str(gb.BOARD_FILE), board)
    print(f"Imported {SES.name}: widened {narrow} thin segments, "
          f"discarded {len(chassis)} router-drawn chassis segments")

    subprocess.run([sys.executable, str(ROOT / "route.py"), "--finish"],
                   check=True)


def finish() -> None:
    board = pcbnew.LoadBoard(str(gb.BOARD_FILE))
    gb.add_chassis_ring(board)
    print("Chassis/PE ring redrawn")

    # Order matters here.  The outer pours have to exist and be filled before
    # anything goes looking for copper to stitch: the routing cuts them into
    # separate pieces, and a piece cannot be found before it has been poured.
    # With the pours added last, seven floating pieces reached DRC untouched.
    poured = gb.add_outer_ground_pours(board)
    print(f"Added {poured} outer-layer ground pours")
    gb.fill_zones(board)

    # Two passes: the standard 0.8 mm via first, then a 0.6 mm one for the
    # few pads left in a strip too tight for it.  0.6 mm is still above the
    # 0.5 mm minimum in the project rules, so this is a smaller via, not a
    # weaker one.
    added = stranded = 0, []
    for via_mm, drill_mm in ((0.8, 0.4), (0.6, 0.3)):
        board.BuildConnectivity()
        count, stranded = gb.add_plane_stitching(board, via_mm, drill_mm)
        print(f"Added {count} stitching vias at {via_mm} mm for supply pads "
              f"the router left unconnected")
    for pad in stranded:
        print(f"  no clear via position for {pad}")

    for via_mm, drill_mm in ((0.8, 0.4), (0.6, 0.3)):
        islands, unreachable_islands = gb.stitch_pour_islands(board, via_mm,
                                                              drill_mm)
        print(f"Stitched {islands} isolated pour pieces at {via_mm} mm")
    for island in unreachable_islands:
        print(f"  no clear via position in {island}")

    board.BuildConnectivity()
    joined, unreachable = gb.close_open_connections(board)
    print(f"Closed {joined} connections the autorouter left open")
    for pad in unreachable:
        print(f"  could not reach {pad}")

    gb.fill_zones(board)
    pcbnew.SaveBoard(str(gb.BOARD_FILE), board)

    # Removing an item degrades KiCad's SWIG proxies for the rest of the
    # process, so the cleanup and the final re-fill each get their own.
    subprocess.run([sys.executable, str(ROOT / "route.py"), "--drop-dangling"],
                   check=True)
    subprocess.run([sys.executable, str(ROOT / "route.py"), "--refill"],
                   check=True)

    board = pcbnew.LoadBoard(str(gb.BOARD_FILE))
    board.BuildConnectivity()
    remaining = board.GetConnectivity().GetUnconnectedCount(True)
    tracks = len(list(board.GetTracks()))
    print(f"Board now has {tracks} track/via items; "
          f"{remaining} unconnected pad pairs remain")


def drop_dangling() -> None:
    board = pcbnew.LoadBoard(str(gb.BOARD_FILE))
    removed = gb.drop_dangling_vias(board)
    pcbnew.SaveBoard(str(gb.BOARD_FILE), board)
    print(f"Removed {removed} vias that connected to nothing")


def refill() -> None:
    board = pcbnew.LoadBoard(str(gb.BOARD_FILE))
    gb.fill_zones(board)
    pcbnew.SaveBoard(str(gb.BOARD_FILE), board)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=100)
    # Freerouting itself warns that multi-threaded optimisation is broken and
    # generates clearance violations; a 4-thread run left 100 of them that no
    # further pass could clear.  Single-threaded is the supported path.
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--export-only", action="store_true")
    parser.add_argument("--import-only", action="store_true")
    parser.add_argument("--drop-dangling", action="store_true",
                        help="internal: remove vias connected to nothing")
    parser.add_argument("--refill", action="store_true",
                        help="internal: re-fill the zones")
    parser.add_argument("--finish", action="store_true",
                        help="internal: re-apply generated copper after import")
    args = parser.parse_args()

    if args.drop_dangling:
        drop_dangling()
        return
    if args.refill:
        refill()
        return
    if args.finish:
        finish()
        return
    if args.import_only:
        import_ses()
        return
    export_dsn()
    if args.export_only:
        return
    run_freerouting(args.passes, args.threads)
    import_ses()


if __name__ == "__main__":
    main()
