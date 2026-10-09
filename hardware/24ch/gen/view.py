"""Render a board region to PNG for a visual check:  python view.py X1 Y1 X2 Y2 out.png [layers]
Uses kicad-cli pcb export pdf + PyMuPDF (system Python 3.10, `pip install pymupdf`)."""
import os
import subprocess
import sys

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
PY310 = r"C:\Users\malgh\AppData\Local\Programs\Python\Python310\python.exe"
x1, y1, x2, y2 = map(float, sys.argv[1:5])
out = sys.argv[5]
layers = sys.argv[6] if len(sys.argv) > 6 else "F.Cu,B.Cu,F.SilkS,Edge.Cuts"
pdf = out + ".pdf"
subprocess.run([CLI, "pcb", "export", "pdf", "--layers", layers, "--mode-single", "--drill-shape-opt", "2",
                "-o", pdf, os.path.join(HW, "thermo24.kicad_pcb")], check=True, capture_output=True)
code = f"""
import fitz
d = fitz.open(r'{pdf}'); p = d[0]
k = 72 / 25.4
# KiCad plots the board at its page position; find the Edge.Cuts frame offset from the drawing bbox
xs = []; ys = []
for g in p.get_drawings():
    r = g['rect']; xs += [r.x0, r.x1]; ys += [r.y0, r.y1]
ox, oy = min(xs), min(ys)
clip = fitz.Rect(ox + {x1} * k, oy + {y1} * k, ox + {x2} * k, oy + {y2} * k)
p.get_pixmap(dpi=600, clip=clip).save(r'{out}')
"""
subprocess.run([PY310, "-c", code], check=True)
os.remove(pdf)
print("wrote", out)
