"""Hand routes of the 8-ch board REV B0 that the routers do badly (2026-10-14), re-applied after a re-route.

    python hand_routes.py [relays] [chassis] [avdd]      (normal python; calls finish.py / delbox.py)

relays  : both relays' contacts as straight 0.8 mm tracks and the first part of the coil feeds. The terminal order (COM, NO, NC)
          against the pin columns forces one crossing per relay: COM and the trip NO run on B.Cu. Clearances
          were worked out against the rules: 0.5 mm inside a relay courtyard, 2 mm contact-to-rest outside.
chassis : J601 pin 1 along the top edge to the plated hole H5, and the C610/R607 bridge beside it.
avdd    : U101 AVDD pin 26 via (24-ch position) and the SYNC pin 27 stub (SYNC tied high, 0039 P8).
Every group first deletes what the router left on those nets in its area, then adds the routes.
Coordinates belong to floor plan v3 (gen/place.py); re-check them when the relays, J601/J701/J702,
U101 or C610/R607 move. The coil feeds end at the driver transistor pads, wherever place.py put them:
they are not drawn here (the router or maze.py connects them).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\Program Files\KiCad\10.0\bin\python.exe"
FINISH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "family", "tools", "finish.py")

RELAY_NETS = ["TRIP_NC", "TRIP_NO", "TRIP_COM", "TRIP_MID", "ALM_NC", "ALM_NO", "ALM_COM", "TRIP_LOW", "ALM_LOW"]
RELAYS = [
    ("+5V", "F.Cu", 0.5, ["60.49,14.49", "58.5,14.49"], True),
    ("TRIP_NC", "F.Cu", 0.8, ["74.05,5.75", "74.05,8.5", "65.0,11.3", "63.5,12.8", "63.5,17.7", "60.49,17.7"], False),
    ("TRIP_COM", "F.Cu", 0.8, ["60.49,19.89", "62.9,20.6"], True),
    ("TRIP_COM", "B.Cu", 0.8, ["62.9,20.6", "64.05,19.45", "64.05,5.75"], False),
    ("TRIP_NO", "B.Cu", 0.8, ["69.05,5.75", "69.05,21.5", "69.6,22.05", "69.6,22.09"], True),
    ("TRIP_NO", "F.Cu", 0.8, ["69.6,22.09", "67.5,22.09"], False),
    ("TRIP_MID", "F.Cu", 0.8, ["60.49,22.09", "64.2,22.09", "66.4,19.89", "67.5,19.89"], False),
    ("TRIP_LOW", "F.Cu", 0.3, ["67.5,14.49", "72.5,14.49", "72.5,27.2"], False),
    ("+5V", "F.Cu", 0.5, ["77.5,14.49", "75.5,14.49"], True),
    ("ALM_NC", "F.Cu", 0.8, ["91.05,5.75", "91.05,8.5", "82.0,11.3", "80.51,12.79", "80.51,17.7", "77.5,17.7"], False),
    ("ALM_COM", "F.Cu", 0.8, ["77.5,19.89", "79.91,20.6"], True),
    ("ALM_COM", "B.Cu", 0.8, ["79.91,20.6", "81.05,19.46", "81.05,5.75"], False),
    ("ALM_NO", "B.Cu", 0.8, ["86.05,5.75", "86.05,23.0", "84.45,24.6", "81.5,24.6"], True),
    ("ALM_NO", "F.Cu", 0.8, ["81.5,24.6", "78.9,24.6", "77.5,23.2", "77.5,22.09"], False),
    ("ALM_LOW", "F.Cu", 0.3, ["84.5,14.49", "92.6,14.49", "93.5,15.4", "93.5,26.8"], False),
]
CHASSIS = [
    ("CHASSIS", "B.Cu", 0.8, ["57.05,5.75", "57.05,0.95", "6.6,0.95", "6.0,2.3"], False),   # B.Cu: the router may run +24V on F.Cu along the edge
    ("CHASSIS", "F.Cu", 0.8, ["1.74,16.0", "1.73,12.5", "2.5,6.3"], False),
    ("GND", "F.Cu", 0.5, ["4.67,12.5", "4.66,16.0"], False),
    ("GND", "F.Cu", 0.5, ["4.66,14.25", "6.6,14.25"], True),
]
AVDD = [
    ("+3V3_ISO", "F.Cu", 0.25, ["49.8,100.56", "49.8,100.0", "50.1,99.7", "50.1,99.62"], True),
    ("+3V3_ISO", "F.Cu", 0.2, ["49.3,100.56", "49.3,100.05", "49.75,100.05"], False),
]
CLEAR = {   # group: (net, box) deleted first
    "relays": [("+5V", (57.5, 12.5, 63.5, 15.5)), ("+5V", (74.5, 12.5, 80.5, 15.5))],
    "chassis": [], "avdd": [("+3V3_ISO", (49.0, 99.0, 50.6, 100.7))],
}


def run(*args):
    r = subprocess.run([PY, *args], capture_output=True, text=True)
    out = [l for l in r.stdout.splitlines() if l.startswith(("add:", "strip:", "delete", "DRC"))]
    print("\n".join(out[-3:]) or r.stderr[-300:])


def main():
    groups = sys.argv[1:] or ["relays", "chassis", "avdd"]
    for g in groups:
        if g == "relays":
            run(FINISH, "--board", "8", "strip", *RELAY_NETS)
        if g == "chassis":
            run(FINISH, "--board", "8", "strip", "CHASSIS")
        for net, box in CLEAR[g]:
            run(os.path.join(HERE, "delbox.py"), net, *map(str, box))
        for net, layer, w, pts, via in {"relays": RELAYS, "chassis": CHASSIS, "avdd": AVDD}[g]:
            run(FINISH, "--board", "8", "add", net, layer, str(w), *pts, *(["via"] if via else []))
    run(FINISH, "--board", "8", "drc")


if __name__ == "__main__":
    main()
