"""ASSEMBLY-SPEC.pdf for the assembler: build preferences, what we ask back, the power-on test (0036 D8).

Written as a request, not as conditions. Needs PyMuPDF (`py -3 -m pip install pymupdf`) and kicad-cli:
    py -3 assembly_spec.py <release folder>
The test-point map is drawn from the board itself (kicad-cli SVG + pos.csv), so it follows the board.
"""
import csv
import os
import subprocess
import sys

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), "thermo24.kicad_pcb")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
W, H = 170.0, 145.0          # board outline, mm; pos.csv origin is the top-left corner, y negative

# test point -> (silkscreen label, reference point, expected value, source)
TESTS = [
    ("TP603", "24V", "GND", "input minus ~0.4 V (23.3 - 24.0 V at 24.0 V in)", "SS310 reverse diode"),
    ("TP602", "5V", "GND", "4.85 - 5.15 V", "LM5164, 1.2 V x (1 + 158k/49.9k) = 5.0 V"),
    ("TP501", "RST", "GND", "4.8 - 5.15 V (MCU not programmed)", "10k pull-up to 5 V"),
    ("TP407", "5VI", "GNDI", "4.5 - 6.5 V (unregulated, rises at light load)", "B0505S isolated module"),
    ("TP401", "3V3I", "GNDI", "3.23 - 3.37 V", "LP2985-3.3"),
    ("TP404", "VREF", "GNDI", "2.99 - 3.01 V", "REF3030"),
    ("TP403", "VMID", "GNDI", "1.60 - 1.70 V", "3.3 V / 2, buffered"),
    ("TP405", "VBIAS", "GNDI", "1.60 - 1.70 V", "VMID through 10k"),
    ("TP406", "REFOK", "GNDI", "J401 open: above 3.0 V.  J401 pin 1 wired to pin 2: below 0.3 V",
     "engine-reference wire check"),
]
REF_TP = {"GND": "TP601", "GNDI": "TP402"}
ORIENT = [
    ("U101, U201, U301", "AD7124-8, LFCSP-32", "pin-1 dot; exposed pad soldered"),
    ("U601", "LM5164, HSOP-8", "pin-1 dot; exposed pad soldered"),
    ("U501", "ATmega1284P, TQFP-44", "pin-1 dot"),
    ("U403, U404, U405", "CA-IS3761, SOIC-16W", "pin-1 mark (they straddle the isolation slot)"),
    ("U102, U103, U202, U203, U302, U303", "TMP126, SC-70-6", "pin-1 mark"),
    ("U401", "B0505S module, THT", "pin 1 to the marked pad"),
    ("C601", "22 uF 100 V electrolytic, THT", "minus stripe to the marked side"),
    ("D601, D602, D603, D701, D711", "SS310, SMBJ60A, SMBJ5.0A, 1N4148W", "cathode band"),
    ("D702 (green RUN), D712 (red ALARM)", "3 mm LEDs, THT", "flat side / short lead to the marked side"),
    ("U703", "ADM2587E, SOIC-20W", "pin-1 mark (straddles the RS-485 isolation slot)"),
    ("J601, J701, J702, J703", "5.00 mm screw terminals", "wire entry toward the board edge (fits both ways)"),
    ("J101-J302, J401", "3.81 mm pluggable headers", "plug opening toward the board edge"),
]
# label offset from the point, mm, where the default would overlap a neighbour or the page edge
LABEL_AT = {"TP401": (3.6, 3.0), "TP601": (-9.5, 6.0), "TP602": (2.0, 6.0), "TP405": (-9.5, 6.0),
            "TP406": (2.0, 6.0)}
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
    name = os.path.basename(rel.rstrip("/\\"))
    tests = [(f"{tp} ({lab})", f"{ref} ({REF_TP[ref]})", exp, src) for tp, lab, ref, exp, src in TESTS]
    return f"""
<h1>Thermo 24-channel board - assembly specification</h1>
<p class="sub">Release {name} &middot; REV A3 &middot; 170 x 145 mm, 4 layers, all parts on the top side</p>
<p>Thank you for quoting this board. This file collects how we would like it built, what we would like
back with it, and the simple power-on test we use. Everything here is a preference: if you work
differently or see a better or cheaper way, please tell us and we will discuss it.</p>

<h2>1. Files in this package</h2>
{table(["File", "Content"], [
    ["thermo24-gerbers.zip", "Gerbers, drill, 4 copper layers, paste layer with the exposed-pad openings"],
    ["BOM.csv", f"{c['lines']} lines, {c['parts']} parts. The LCSC column is a reference number only; equivalents welcome"],
    ["CPL.csv", f"placement of all {c['parts']} parts (top side)"],
    ["DNP.txt", "footprints that stay empty (section 6)" if dnp else "every footprint is fitted"],
    ["ACCESSORIES.csv", "loose items: mating plugs, cable housing, LCD socket, standoffs"],
    ["ORDER-NOTES.txt", "short version of this file"],
    ["ASSEMBLY-SPEC.pdf", "this file"]])}

<h2>2. Quantity</h2>
<p>Please quote <b>5 boards</b> and <b>10 boards</b>. If you can build <b>one board first</b> for us to check
before the rest, please tell us what that changes in price and time.</p>

<h2>3. Bare board (preferred)</h2>
{table(["Item", "Preference"], [
    ["Material, thickness", "FR-4, 1.6 mm, 1 oz copper on all 4 layers"],
    ["Surface finish", "<b>ENIG</b> (fine-pitch and exposed-pad parts). If your price is for HASL, please show the difference"],
    ["Solder mask / silkscreen", "green / white; vias covered (tented)"],
    ["Electrical test", "bare-board test (flying probe or fixture)"]])}

<h2>4. Assembly (preferred)</h2>
{table(["Item", "Preference"], [
    ["SMD parts", f"{c['smd']} parts, machine placement and reflow"],
    ["Stencil", "laser-cut steel, about 0.12 mm (0.5 mm pitch parts); the paste layer already has the windows"],
    ["Solder paste", "your standard paste (lead-free or leaded both fine; please tell us which)"],
    ["Exposed pads", "AD7124-8 x3 (U101, U201, U301) and LM5164 (U601) have a pad underneath that must be soldered. "
                     "X-ray check if you have it; otherwise the power-on test in section 8 proves U601"],
    ["Moisture-sensitive ICs", "handled or baked per their MSL rating"],
    ["Through-hole parts", f"{c['tht']} ({c['n_tht']} parts): hand or selective soldering, seated flat"],
    ["Cleaning", "<b>please wash off the flux</b> (IPA or aqueous) and dry. The thermocouple inputs are "
                 "high-impedance; flux residue in the area marked ISOLATED SENSOR SIDE becomes a measurement error"]])}

<h2>5. Orientation checklist</h2>
{table(["Reference", "Part", "Check"], ORIENT)}

<h2>6. Not fitted by you</h2>
<p>{("Please leave these footprints empty (not in the BOM or CPL): " + dnp + ". ") if dnp else
   "Every footprint on the board is fitted, including the RS-485 block (U703, J703) and the headers JP731-JP733 (no jumper shunts: they are set at the site). "}
Please do <b>not</b> fit the LCD module and do <b>not</b> program the microcontroller: we do both.</p>

<h2>7. Accuracy parts</h2>
<p>AD7124-8, TMP126, BAV199, the 20M and 1 % resistors and the C0G capacitors set the measurement
accuracy. If one of them is hard to get, we would be grateful for a word before an alternative is used.</p>

<h2>8. Power-on test (please quote it as an option)</h2>
<p>No firmware is needed. Supply <b>24.0 V</b> with the current limit set to <b>150 mA</b> on J601
(+24V and 0V), nothing else connected. Measure with a multimeter. The isolated side has its own
ground: measure each point against the ground named in the table, <b>GND (TP601)</b> or <b>GNDI (TP402)</b>.</p>
{table(["Test point (silkscreen)", "Measure against", "Expected", "Set by"], tests)}
<p>Also record: <b>input current</b> at 24 V (normal is well below 100 mA; the boards should agree with each
other within about 20 %), and, <b>with power off</b>, the resistance from GND (TP601) to GNDI (TP402):
the meter must show <b>open</b> (above 10 Mohm). A board outside any range: please stop and tell us.</p>
<p>Where the points are: see the <b>test-point map on the last page</b>.</p>

<h2>9. What we would like back</h2>
<ul>
<li>Quotation split into: bare board, assembly, parts, stencil/setup, and each option (one board first,
power-on test, conformal coating, accessories); lead time; how long the offer is valid.</li>
<li>Any part you could not find or would replace, before the build.</li>
<li>Boards numbered 01, 02, ... (marker on the board is fine), packed in ESD bags.</li>
<li>If the power-on test is ordered: the readings per board number (a photo of a filled table is fine).</li>
<li>What happens if a soldering fault is found after delivery (rework terms).</li>
</ul>

<h2>10. Our checks after delivery (for your information)</h2>
<ol>
<li>Visual check and the power-on test of section 8 on every board.</li>
<li>Isolation check GND to GNDI.</li>
<li>Programming through the 6-pin ISP header J501.</li>
<li>Full function: all 24 thermocouple channels read, the trip and alarm relays switch.</li>
</ol>
<p>A fault that traces back to assembly we would like to return to you for rework.</p>

<h2>11. Optional: conformal coating</h2>
<p>If you offer it: acrylic conformal coating (IPC-CC-830 type), both sides, <b>after</b> washing and
testing, with connectors, pin headers, buttons, relays, test points and the LCD header masked.
If not, we will do it ourselves.</p>

<h2>12. Accessories (ACCESSORIES.csv)</h2>
<p>Mating plugs 3.81 mm 8-pin x6 and 2-pin x1, XH 6-pin housing with contacts, LCD 16-pin socket,
2.54 mm jumper shunts x3 (loose, for JP731-JP733),
M3 x 10 standoffs. If you also have the 3.81 mm plugs and headers in other colours, please quote them.</p>
"""


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
