"""Rename nets on the board without touching copper (I-062).

    <KiCad python> hardware/8ch/sch_layout/rename_board_nets.py BOARD MAP.json

MAP.json is {old name: new name}, as written by
``netlist_fingerprint.py OLD NEW --allow-renames MAP.json`` - which only
writes it when every pin is still on the same net. Pads, tracks, vias and
zones all point at one NETINFO item per net, so renaming that item renames
them together. ``kicad-tool pcb sync`` does not do this: it moves the pads to
the new name and leaves the tracks on the old one, which DRC then reports as
hundreds of clearance errors between a track and its own pad.

Run ``kicad-tool pcb sync`` afterwards to re-link footprints to the
hierarchical symbol paths, then DRC with --schematic-parity.
"""
import json
import sys

import pcbnew


def main():
    board_file, map_file = sys.argv[1:3]
    renames = json.load(open(map_file, encoding="utf-8"))
    board = pcbnew.LoadBoard(board_file)
    nets = board.GetNetsByName()
    done, missing = 0, []
    for old, new in renames.items():
        if board.FindNet(new) is not None:
            raise SystemExit(f"{new} already exists on the board - refusing to merge nets")
        net = board.FindNet(old)
        if net is None:
            missing.append(old)
            continue
        net.SetNetname(new)
        done += 1
    if missing:
        raise SystemExit(f"not on the board: {missing}")
    board.GetNetInfo().RebuildDisplayNetnames()
    pcbnew.SaveBoard(board_file, board)
    print(f"renamed {done} nets on {board_file}")


if __name__ == "__main__":
    main()
