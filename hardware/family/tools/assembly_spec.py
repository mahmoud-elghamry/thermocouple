"""ASSEMBLY-SPEC.pdf for the assembler: build preferences, what we ask back, the power-on test (0036 D8).

Written as a request, not as conditions. Needs PyMuPDF (`py -3 -m pip install pymupdf`) and kicad-cli:
    py -3 assembly_spec.py <release folder>
The test-point map is drawn from the board itself (kicad-cli SVG + pos.csv), so it follows the board.
"""

from profiles import ACTIVE as P, ROOT
import csv
import os
import subprocess
import sys

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = str(P["pcb"])
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
W, H = P.require("width"), P.require("height")

# test point -> (silkscreen label, reference point, expected value, source)
TESTS = P.require("assembly")["TESTS"]
REF_TP = P.require("assembly")["REF_TP"]
ORIENT = P.require("assembly")["ORIENT"]
# label offset from the point, mm, where the default would overlap a neighbour or the page edge
LABEL_AT = P.require("assembly")["LABEL_AT"]
THT_FP = ("CP_Radial", "LED_D3.0mm", "PhoenixContact_MC", "PinHeader", "JST_XH", "TerminalBlock",
          "Potentiometer", "SW_PUSH", "_THT")     # footprint names of through-hole parts


def counts(rel):
    """BOM lines, parts, and the through-hole references, read from the release's BOM.csv."""
    rows = list(csv.DictReader(open(os.path.join(rel, "BOM.csv"), encoding="utf-8")))
    tht = sorted((r for row in rows if any(k in row["Footprint"] for k in THT_FP)
                  for r in row["Designator"].split(",")), key=lambda r: (r.rstrip("0123456789"), int(r[len(r.rstrip("0123456789")):])))
    parts = sum(int(row["Qty"]) for row in rows)
    return {"lines": len(rows), "parts": parts, "smd": parts - len(tht), "tht": ", ".join(tht), "n_tht": len(tht)}


def tp_map(rel, out_png):
    svg = out_png[:-4] + ".svg"
    subprocess.run([KICAD_CLI, "pcb", "export", "svg", "--mode-single", "-o", svg, "--layers",
                    "F.Silkscreen,Edge.Cuts,F.Mask", "--page-size-mode", "2", "--exclude-drawing-sheet",
                    "--black-and-white", BOARD], check=True, capture_output=True)
    doc = fitz.open(svg)
    pdf = fitz.open("pdf", doc.convert_to_pdf())
    page = pdf[0]
    k = page.rect.width / W
    pos = {r[0]: (float(r[3]), -float(r[4])) for r in csv.reader(open(os.path.join(rel, "pos.csv")))
           if r and r[0].startswith("TP")}
    for tp, (x, y) in pos.items():
        c = fitz.Point(x * k, y * k)
        page.draw_circle(c, 3.2 * k, color=(0.85, 0, 0), width=1.6)
        dx, dy = LABEL_AT.get(tp, (3.6, -2.2))
        page.insert_text(c + (dx * k, dy * k), tp, fontsize=7.5, color=(0.85, 0, 0), fontname="hebo")
    page.get_pixmap(dpi=170).save(out_png)
    os.remove(svg)


def table(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{b}</table>"


def html(rel, dnp, c):
    return P.require("assembly_html")(rel, dnp, c, table)


CSS = """
body {font-family: sans-serif; font-size: 9pt; line-height: 1.3;}
h1 {font-size: 15pt; margin: 0;} h2 {font-size: 11pt; margin-top: 12px; margin-bottom: 4px; color: #0b3d6b;}
.sub {color: #555; margin-top: 2px;} .cap {font-size: 8pt; color: #555;}
table {border-collapse: collapse; width: 100%; margin: 3px 0;}
th, td {border: 0.5px solid #999; padding: 3px 4px; text-align: left; vertical-align: top;}
th {font-weight: bold;}
"""


def main(rel):
    work = os.path.join(rel, "_spec_tmp")
    os.makedirs(work, exist_ok=True)
    tp_map(rel, os.path.join(work, "tp_map.png"))
    dnp = open(os.path.join(rel, "DNP.txt"), encoding="utf-8").read().splitlines()[1].strip()
    dnp = "" if dnp.startswith("none") else dnp
    story = fitz.Story(html=html(rel, dnp, counts(rel)), user_css=CSS)
    out = os.path.join(rel, "ASSEMBLY-SPEC.pdf")
    writer = fitz.DocumentWriter(out)
    more = True
    while more:
        dev = writer.begin_page(fitz.paper_rect("a4"))
        more, _ = story.place(fitz.paper_rect("a4") + (40, 40, -40, -40))
        story.draw(dev)
        writer.end_page()
    writer.close()
    doc = fitz.open(out)              # the map on its own landscape page, full width
    page = doc.new_page(width=842, height=595)
    page.insert_text((40, 45), "Test-point map (section 8) - red circles, drawn from the board file", fontsize=12,
                     fontname="hebo")
    page.insert_text((40, 62), "Silkscreen labels: 24V, GND, 5V, RST (power side); 5VI, GNDI, 3V3I, VREF, VMID, "
                     "VBIAS, REFOK (isolated side)", fontsize=9)
    page.insert_image(fitz.Rect(40, 72, 802, 575), filename=os.path.join(work, "tp_map.png"))
    doc.saveIncr()
    for f in os.listdir(work):
        os.remove(os.path.join(work, f))
    os.rmdir(work)
    print("written", out, fitz.open(out).page_count, "pages")


if __name__ == "__main__":
    main(sys.argv[1])
