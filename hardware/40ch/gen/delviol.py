"""Delete the copied (copy24.py) tracks and vias that take part in a DRC violation.

    python delviol.py BOARD REFERENCE_BOARD [DRC_JSON]
Items whose UUID is also in REFERENCE_BOARD (the board before the copy) are never touched; of the rest, every
track/via named in a violation of output/finish-drc.json (or DRC_JSON) is removed. Run with KiCad's python.
"""
import json
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))


def main(board, ref, report):
    keep = {t.m_Uuid.AsString() for t in pcbnew.LoadBoard(ref).GetTracks()}
    b = pcbnew.LoadBoard(board)
    by_id = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
    bad = set()
    for v in json.load(open(report, encoding="utf-8")).get("violations", []):
        for it in v["items"]:
            u = it.get("uuid")
            if u in by_id and u not in keep:
                bad.add(u)
    for u in bad:
        b.Remove(by_id[u])
    pcbnew.SaveBoard(board, b)
    print(f"delviol: removed {len(bad)} copied items")


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]),
         sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(HERE), "output", "finish-drc.json"))
