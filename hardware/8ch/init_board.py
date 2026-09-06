"""Create the empty four-layer carrier before kicad-tool schematic sync.

The structural source is the schematic. This initializer only establishes
the board stack-up and file container; kicad-tool adds and nets footprints.
"""

from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "thermocouple_8ch.kicad_pcb"

board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
pcbnew.SaveBoard(str(OUT), board)
print(f"Initialized {OUT}")
