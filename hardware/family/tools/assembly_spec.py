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
import zipfile

from manifest_complete import rewrite_manifest

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_CLI = os.environ.get('KICAD_CLI', r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
W, H = P.require("width"), P.require("height")

# test point -> (silkscreen label, reference point, expected value, source)
TESTS = P.require("assembly")["TESTS"]
REF_TP = P.require("assembly")["REF_TP"]
ORIENT = P.require("assembly")["ORIENT"]
# label offset from the point, mm, where the default would overlap a neighbour or the page edge
LABEL_AT = P.require("assembly")["LABEL_AT"]
MAP_POINTS = list(dict.fromkeys([r[0] for r in TESTS] + list(REF_TP.values())))
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
    import fitz

    svg = out_png[:-4] + ".svg"
    board = os.path.join(rel, 'source-snapshot', P['project'] + '.kicad_pcb')
    if not os.path.isfile(board):
        raise FileNotFoundError(f'test-point map requires release snapshot: {board}')
    subprocess.run([KICAD_CLI, "pcb", "export", "svg", "--mode-single", "-o", svg, "--layers",
                    "F.Silkscreen,Edge.Cuts,F.Mask", "--page-size-mode", "2", "--exclude-drawing-sheet",
                    "--black-and-white", board], check=True, capture_output=True)
    doc = fitz.open(svg)
    pdf = fitz.open("pdf", doc.convert_to_pdf())
    page = pdf[0]
    k = page.rect.width / W
    pos = {r[0]: (float(r[3]), -float(r[4])) for r in csv.reader(open(os.path.join(rel, "pos.csv")))
           if r and r[0].startswith("TP")}
    for tp in MAP_POINTS:
        if tp not in pos:
            raise ValueError(f'{tp}: test point missing from release pos.csv')
        x, y = pos[tp]
        c = fitz.Point(x * k, y * k)
        page.draw_circle(c, 2.3 * k, color=(0.85, 0, 0), width=1.6)
        # Short number tags remain legible where several test pads are adjacent.
        tag = str(MAP_POINTS.index(tp) + 1)
        dx, dy = LABEL_AT.get(tp, (2.5, -1.5))
        page.insert_text(c + (dx * k, dy * k), tag, fontsize=8.5, color=(0.85, 0, 0), fontname="hebo")
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
    import fitz

    work = os.path.join(rel, "_spec_tmp")
    os.makedirs(work, exist_ok=True)
    tp_map(rel, os.path.join(work, "tp_map.png"))
    power_on_test(rel, os.path.join(work, "tp_map.png"))
    fitted = {r.strip() for row in csv.DictReader(open(os.path.join(rel, 'BOM.csv'), encoding='utf-8-sig'))
              for r in row['Designator'].split(',')}
    exposed = {r for r in fitted if r in P['adc_refs'] or r == 'U601' or r == 'U1001'}
    polarity = fitted & {'K701', 'K702', 'U401'}
    which, notes, _ = handoff_texts(os.path.basename(os.path.normpath(rel)), P, exposed, polarity)
    with open(os.path.join(rel, 'WHICH-FILE-WHERE.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(which)
    path = os.path.join(rel, 'ORDER-NOTES.txt')
    old = open(path, encoding='utf-8').read()
    head = 'IF YOU ORDER ON THE JLCPCB WEBSITE'
    old = old.split(head, 1)[0].rstrip() + '\n'
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(old + '\n' + notes)
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
    page = doc.new_page(width=1191, height=842)
    page.insert_text((40, 45), "Test-point map (section 8) - red circles, release source snapshot", fontsize=12,
                     fontname="hebo")
    page.insert_image(fitz.Rect(40, 72, 935, 812), filename=os.path.join(work, "tp_map.png"))
    map_legend(page, 950)
    doc.saveIncr()
    for f in os.listdir(work):
        os.remove(os.path.join(work, f))
    os.rmdir(work)
    if os.path.exists(os.path.join(rel, 'MANIFEST.txt')):
        rewrite_manifest(rel)
    print("written", out, fitz.open(out).page_count, "pages")


def handoff_texts(name, profile, exposed, polarity):
    """Supplier-facing directions; all references come from the fitted BOM."""
    project = profile['project']
    xrays = ','.join(sorted(exposed))
    pins = ','.join(sorted(polarity))
    remark = (f'Apply 24.0V to J601 (+24V,0V), limit 150mA; no firmware. '
              f'Measure TP603 23.3-24.0V and TP602 4.85-5.15V vs TP601 GND; '
              f'TP401 3.23-3.37V and TP404 2.99-3.01V vs TP402 GNDI. '
              f'Off: GND-GNDI open >10Mohm. Send readings per board; stop if out of range. '
              f'X-ray exposed pads {xrays}; send images. Wash flux. '
              f'Check pin 1/polarity {pins}. Check all refs in JLC-PLACEMENT-REVIEW.txt against preview.')
    if len(remark) > 500:
        raise ValueError(f'JLC remark exceeds 500 characters ({len(remark)})')
    which = (f'WHICH FILE GOES WHERE - {name}\n\n'
             f'JLCPCB website: {project}-gerbers.zip as Gerber; BOM.csv and CPL-JLC.csv on assembly step.\n'
             'CPL-JLC.csv has package rotation hypotheses and drilled-pad centring for JLC; inspect EVERY '
             'polarized/directional reference in JLC-PLACEMENT-REVIEW.txt in the placement preview.\n'
             'Attach POWER-ON-TEST.zip to the PCBA Function test option; paste the remark below.\n\n'
             'Other assembler / quotation: use raw KiCad CPL.csv with BOM.csv, Gerbers, ASSEMBLY-SPEC.pdf, '
             'POWER-ON-TEST.pdf, ORDER-NOTES.txt and ACCESSORIES.csv.\n'
             'Outside reviewer: schematic PDF, BOM, Gerbers, assembly spec, and source snapshot.\n\n'
             f'Assembly remark (self-contained; {len(remark)}/500 characters):\n{remark}\n')
    notes = ('IF YOU ORDER ON THE JLCPCB WEBSITE\n'
             f'- Upload {project}-gerbers.zip as Gerber, BOM.csv and CPL-JLC.csv for assembly.\n'
             '- CPL.csv is the raw KiCad placement list for other assemblers.\n'
             '- Inspect all polarized/directional references in JLC-PLACEMENT-REVIEW.txt against the JLC preview; '
             'package rotations for this board are not established by generation alone.\n'
             '- Attach POWER-ON-TEST.zip to PCBA Function test.\n'
             f'- Paste this self-contained assembly remark ({len(remark)}/500 characters):\n{remark}\n')
    return which, notes, remark


def map_legend(page, x):
    for i, tp in enumerate(MAP_POINTS, 1):
        label = next((row[1] for row in TESTS if row[0] == tp),
                     next((name for name, ref in REF_TP.items() if ref == tp), ''))
        page.insert_text((x, 88 + i * 28), f'{i:2d}  {tp}  {label}', fontsize=11, fontname='hebo')


def power_on_test(rel, png):
    """Standalone two-page test and identical PDF inside JLC's upload ZIP."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 48

    def line(value, size=10, bold=False):
        nonlocal y
        page.insert_text((45, y), value, fontsize=size, fontname='hebo' if bold else 'helv')
        y += size + 6

    line(f'Thermo {P["channels"]}-channel {P["revision"]} - power-on test', 13, True)
    line(f'Release: {os.path.basename(os.path.normpath(rel))}')
    line('No firmware needed. Use a current-limited supply and multimeter.')
    y += 10
    for step in ('1. Connect nothing except 24.0 V on J601 (+24V, 0V); limit 150 mA.',
                 '2. Record input current; estimate below 100 mA.',
                 '3. Measure the points below against the stated ground.',
                 '4. Turn power off. GND (TP601) to GNDI (TP402): open, >10 Mohm.',
                 '5. Stop and report any out-of-range value before shipping.'):
        line(step)
    y += 10
    line('Point (silk)       Ground reference      Expected', 10, True)
    short = {'TP603': '23.3 - 24.0 V', 'TP406': 'J401 open: >3.0 V'}
    for tp, label, ground, expected, _ in TESTS:
        value = short.get(tp, expected.split(' (')[0])
        line(f'{tp} ({label})       {REF_TP[ground]} ({ground})       {value}', 9)
    line('Link J401 pins 1 and 2: TP406 must fall below 0.3 V vs GNDI (TP402).', 9)
    y += 10
    line('Send readings for each board and X-ray images of exposed pads.', 10, True)
    line('See page 2 for test-point locations on this release board.')
    page = doc.new_page(width=1191, height=842)
    page.insert_text((40, 45), 'Test-point map - release source snapshot', fontsize=12, fontname='hebo')
    page.insert_image(fitz.Rect(40, 65, 935, 812), filename=png)
    map_legend(page, 950)
    out = os.path.join(rel, 'POWER-ON-TEST.pdf')
    doc.save(out)
    doc.close()
    with zipfile.ZipFile(os.path.join(rel, 'POWER-ON-TEST.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(out, 'POWER-ON-TEST.pdf')


if __name__ == "__main__":
    main(sys.argv[1])
