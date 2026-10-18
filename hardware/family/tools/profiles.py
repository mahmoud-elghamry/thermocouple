"""One board profile; consume --board/--pcb before the legacy tool parses arguments.

Unknown geometry is deliberately None, never an estimated manufacturing value.
Copy overrides also redirect sidecars and output beside the copy. Child processes
inherit the selection. Geometry stays in each board's own gen/rules.py.
"""
import importlib.util
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
class Profile(dict):
    def require(self, name):
        value = self[name]
        if value is None:
            raise SystemExit(f"profile {self['key']}: {name}: set by floor plan")
        return value
PROFILES = {}
for key, folder, adcs in (
        ('24', '24ch', ('U101', 'U201', 'U301')), ('8', '8ch-new', ('U101',)),
        ('40', '40ch', ('U101', 'U201', 'U301', 'U801', 'U901'))):
    PROFILES[key] = Profile(
        key=key, project='thermo' + key, folder=ROOT / 'hardware' / folder,
        channels=int(key), adc_refs=adcs, banks=tuple(range(1, len(adcs) + 1)),
        bank_ref_bases=tuple(int(r[1:]) - 1 for r in adcs),
        rtd_adc=None, decoder_ref=None, sio_driver_ref=None, mounting_hole_types=None,  # set by floor plan
        width=None, height=None, outline=None, mounting_holes=None,  # set by floor plan
        fiducials=None, silk=None, pin_checks=None, buck_ref=None,  # set by floor plan
        plane_nets=None, plane_domains=None, contact_nets=None,  # set by floor plan
        chassis_net=None, high_clearance_nets=None, keep_nets=None,  # set by floor plan
        keep_prefix=None, classes=None, pair_rules=None, revision=None,  # set by floor plan
        bias_net=None, island_prefix=None, bias_prefix=None,  # set by floor plan
        bank_channels=None, board_only=None, assembly=None, assembly_html=None,  # set by floor plan
        release_prefix=None, exposed_pad_text=None, order_notes=None, bootstrap_nets=None,  # set by floor plan
    )
PROFILES['40'].update(rtd_adc='U1001', decoder_ref='U410', sio_driver_ref='U411')
PROFILES['8'].update(width=130.0, height=137.0, outline=((0, 0), (130, 0), (130, 137), (0, 137)),
    revision='REV B0', bank_channels=(8,), buck_ref='U601',
    mounting_holes={'H5': (4.5, 4.5), 'H4': (126, 40), 'H6': (4.5, 29.5), 'H7': (97.5, 29.5), 'H8': (4.5, 84.5),
                    'H9': (97.5, 84.5), 'H1': (4.5, 132.5), 'H3': (125.5, 132.5), 'H2': (4.5, 100), 'H10': (90, 113)},
    mounting_hole_types={'H5': 'chassis-plated', 'H4': 'plain NPTH (0039 P9)', **dict.fromkeys(
        ('H6', 'H7', 'H8', 'H9'), 'LCD standoff'), **dict.fromkeys(('H1', 'H3', 'H2', 'H10'), 'island NPTH')})
P24 = PROFILES['24']
P24.update(
    width=170.0, height=145.0, outline=((0, 0), (170, 0), (170, 145), (0, 145)),
    mounting_holes={'H1': (4.5, 140.5), 'H2': (4.5, 101), 'H3': (165.5, 140.5),
                    'H4': (165.5, 92), 'H5': (165.5, 4.5), 'H10': (4.5, 4.5),
                    'H6': (49.5, 41.5), 'H7': (142.5, 41.5), 'H8': (49.5, 96.5), 'H9': (142.5, 96.5)},
    fiducials={'FID1': (10.0, 10.0), 'FID2': (160.0, 12.0), 'FID3': (10.0, 135.0)},
    plane_nets={'GND_ISO', 'GND', 'GND_RS485', '+3V3_ISO', '+5V'},
    plane_domains={'GND_ISO': 'ISLAND', '+3V3_ISO': 'ISLAND', 'GND': 'CONTROL', '+5V': 'CONTROL'},
    contact_nets={'TRIP_COM', 'TRIP_NO', 'TRIP_NC', 'TRIP_MID', 'ALM_COM', 'ALM_NO', 'ALM_NC'},
    chassis_net='CHASSIS',
    high_clearance_nets={'+24V_RAW', '+24V_FUSED', '+24V_PROT', 'RS485_A', 'RS485_B'},
    keep_nets={'CHASSIS', 'V_BIAS', 'VREF_EXT'}, keep_prefix=('REGCAP', 'REFOUT_', 'SYNC_'),
    classes=('kicad_default', 'Island', 'IslandPower', 'CtrlPower', 'Power24V', 'RS485', 'Chassis', 'Contact'),
    pair_rules=(('Contact', ('Contact',), 2.0), ('Chassis', ('Chassis', 'Contact'), 1.5)),
    revision='REV A4', bias_net='V_BIAS', island_prefix='ISLAND_', bias_prefix='VBIAS_GUARD',
    bank_channels=(8, 8, 8), board_only=('FID',), buck_ref='U601', release_prefix='24ch-reva4',
    sio_driver_ref='U411',
    exposed_pad_text='The three AD7124-8 (5x5 mm LFCSP) and the LM5164', bootstrap_nets=('BST_5V', 'SW_5V'),
)
P24['pin_checks'] = [('U601', '2', 3.0, 'LM5164 VIN ceramic input cap'),
    ('U601', '7', 3.0, 'LM5164 BST bootstrap cap (BST-SW)'),
    ('U601', '8', 3.0, 'LM5164 SW side of the bootstrap cap'),
    ('U601', '5', 5.0, 'LM5164 FB divider (R or C)'),
] + [(u, pin, 3.0, what) for u in ('U403', 'U404', 'U405')
     for pin, what in (('1', 'ISO7761 VCC1'), ('16', 'ISO7761 VCC2'))] + [
    ('U411', '5', 3.0, '74LVC1G125 VCC (REV A4 SIO driver)')
] + [
    (u, pin, lim, what) for u in P24['adc_refs'] for pin, lim, what in (
        ('26', 'plane', 'AD7124 AVDD'), ('2', 'plane', 'AD7124 IOVDD'),
        ('24', 5.0, 'AD7124 REGCAPA'), ('1', 5.0, 'AD7124 REGCAPD'),
        ('22', 5.0, 'AD7124 REFOUT (internal ref is the TC reference, 0032)'))
] + [('U501', pin, 3.0, what) for pin, what in (
    ('5', 'ATmega VCC'), ('17', 'ATmega VCC'), ('38', 'ATmega VCC'), ('27', 'ATmega AVCC'))]
P24['silk'] = dict(
    barriers=((43.5, 12.5, 43.5, 101.5), (43.5, 101.5, 169.5, 101.5),
              (53.5, 0.5, 53.5, 23.5), (53.5, 23.5, 85.5, 23.5), (85.5, 23.5, 85.5, 0.5)),
    horizontal=('J101', 'J102', 'J201', 'J202'), vertical=('J301', 'J302'),
    horizontal_y=133.4, vertical_sign_x=11.4, vertical_number_x=11.3,
    terminals=(('J601', ('+24V', '0V', 'CHAS'), 'SUPPLY'),
               ('J701', ('C', 'NO', 'NC'), 'RUN PERMIT C-NO'), ('J702', ('C', 'NO', 'NC'), 'ALARM')),
    terminal_y=12.3, terminal_title_y=15.5, bus_ref='J703', bus_y=14.6,
    jumpers=(('JP731', 'TERM'), ('JP732', 'BIAS A'), ('JP733', 'BIAS B')),
    lcd_ref='J502', buttons_ref='J503', isp_ref='J501', refs_if_room=('J', 'U', 'K', 'Y', 'L6'),
    functions={'SW501': 'UP', 'SW502': 'DOWN', 'SW503': 'SET', 'SW504': 'ESC', 'SW505': 'ACK',
               'D702': 'RUN', 'D712': 'ALARM', 'RV501': 'LCD CONTRAST', 'F601': '0.75A',
               'TP401': '3V3I', 'TP402': 'GNDI', 'TP403': 'VMID', 'TP404': 'VREF', 'TP405': 'VBIAS',
               'TP406': 'REFOK', 'TP407': '5VI', 'TP501': 'RST', 'TP601': 'GND', 'TP602': '5V', 'TP603': '24V'},
    fixed=(('ENGINE REF: 1 FEED 2 SENSE', 7.8, 97.6, (0.6, 0.8), {'reach': 2.5}),
           ('2 WIRES, JOINED ONLY AT THE ENGINE', 7.8, 96.2, (0.6, 0.8), {'reach': 3.0, 'must': False}),
           ('K-TYPE TC: n+ / n-', 30.0, 131.0, 0.9, {'reach': 6, 'must': False}),
           ('CONTACTS: LOW-VOLTAGE SIGNAL LOAD ONLY, 30 VDC / 1 A MAX', 103.0, 40.0, 1.0, {'bold': True, 'reach': 4}),
           ('THERMO 24-CH  REV A4', 106.0, 84.0, 1.5, {'bold': True, 'reach': 6}),
           ('ISOLATED SENSOR SIDE', 20.0, 104.5, 1.0, {'reach': 5})),
)
P24["assembly"] = {'TESTS': [
        ('TP603', '24V', 'GND', 'input minus ~0.4 V (23.3 - 24.0 V at 24.0 V in)', 'SS310 reverse diode'),
        ('TP602', '5V', 'GND', '4.85 - 5.15 V', 'LM5164, 1.2 V x (1 + 158k/49.9k) = 5.0 V'),
        ('TP501', 'RST', 'GND', '4.8 - 5.15 V (MCU not programmed)', '10k pull-up to 5 V'),
        ('TP407', '5VI', 'GNDI', '4.5 - 6.5 V (unregulated, rises at light load)', 'B0505S isolated module'),
        ('TP401', '3V3I', 'GNDI', '3.23 - 3.37 V', 'LP2985-3.3'), ('TP404', 'VREF', 'GNDI', '2.99 - 3.01 V', 'REF3030'),
        ('TP403', 'VMID', 'GNDI', '1.60 - 1.70 V', '3.3 V / 2, buffered'),
        ('TP405', 'VBIAS', 'GNDI', '1.60 - 1.70 V', 'VMID through 10k'),
        ('TP406', 'REFOK', 'GNDI', 'J401 open: above 3.0 V.  J401 pin 1 wired to pin 2: below 0.3 V', 'engine-reference wire check'),
    ], 'REF_TP': {'GND': 'TP601', 'GNDI': 'TP402'},
    'ORIENT': [('U101, U201, U301', 'AD7124-8, LFCSP-32', 'pin-1 dot; exposed pad soldered'),
        ('U601', 'LM5164, HSOP-8', 'pin-1 dot; exposed pad soldered'), ('U501', 'ATmega1284P, TQFP-44', 'pin-1 dot'),
        ('U403, U404, U405', 'CA-IS3761, SOIC-16W', 'pin-1 mark (they straddle the isolation slot)'),
        ('U102, U103, U202, U203, U302, U303', 'TMP126, SC-70-6', 'pin-1 mark'),
        ('U401', 'B0505S module, THT', 'pin 1 to the marked pad'), ('C601', '22 uF 100 V electrolytic, THT', 'minus stripe to the marked side'),
        ('D601, D602, D603, D701, D711', 'SS310, SMBJ60A, SMBJ5.0A, 1N4148W', 'cathode band'),
        ('D702 (green RUN), D712 (red ALARM)', '3 mm LEDs, THT', 'flat side / short lead to the marked side'),
        ('U703', 'ADM2587E, SOIC-20W', 'pin-1 mark (straddles the RS-485 isolation slot)'),
        ('J601, J701, J702, J703', '5.00 mm screw terminals', 'wire entry toward the board edge (fits both ways)'),
        ('J101-J302, J401', '3.81 mm pluggable headers', 'plug opening toward the board edge'),
    ], 'LABEL_AT': {'TP401': (3.6, 3.0), 'TP601': (-9.5, 6.0), 'TP602': (2.0, 6.0), 'TP405': (-9.5, 6.0), 'TP406': (2.0, 6.0)},
}
def assembly24_html(rel, dnp, c, table, P=None, text=None):
    P, text = P24 if P is None else P, text or {}
    TESTS, REF_TP, ORIENT = (P["assembly"][k] for k in ("TESTS", "REF_TP", "ORIENT"))
    name = os.path.basename(rel.rstrip("/\\"))
    tests = [(f"{tp} ({lab})", f"{ref} ({REF_TP[ref]})", exp, src) for tp, lab, ref, exp, src in TESTS]
    return f"""
<h1>Thermo {P['channels']}-channel board - assembly specification</h1>
<p class="sub">Release {name} &middot; {P['revision']} &middot; {P['width']:g} x {P['height']:g} mm, {P.get('copper_layers', 4)} layers, all parts on the top side</p>
<p>Thank you for quoting this board. This file collects how we would like it built, what we would like
back with it, and the simple power-on test we use. Everything here is a preference: if you work
differently or see a better or cheaper way, please tell us and we will discuss it.</p>

<h2>1. Files in this package</h2>
{table(["File", "Content"], [
    [P['project'] + "-gerbers.zip", f"Gerbers, drill, {P.get('copper_layers', 4)} copper layers, paste layer with the exposed-pad openings"],
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
    ["Material, thickness", f"FR-4, 1.6 mm, 1 oz copper on all {P.get('copper_layers', 4)} layers"],
    ["Surface finish", "<b>ENIG</b> (fine-pitch and exposed-pad parts). If your price is for HASL, please show the difference"],
    ["Solder mask / silkscreen", "green / white; vias covered (tented)"],
] + ([["Smallest features (please confirm)", P["fab_limits"]]] if P.get("fab_limits") else []) + [
    ["Electrical test", "bare-board test (flying probe or fixture)"]])}

<h2>4. Assembly (preferred)</h2>
{table(["Item", "Preference"], [
    ["SMD parts", f"{c['smd']} parts, machine placement and reflow"],
    ["Stencil", "laser-cut steel, about 0.12 mm (0.5 mm pitch parts); the paste layer already has the windows"],
    ["Solder paste", "your standard paste (lead-free or leaded both fine; please tell us which)"],
    ["Exposed pads", text.get('exposed_pads', "AD7124-8 x3 (U101, U201, U301) and LM5164 (U601) have a pad underneath that must be soldered. "
                     "X-ray check if you have it; otherwise the power-on test in section 8 proves U601")],
    ["Moisture-sensitive ICs", "handled or baked per their MSL rating"],
    ["Through-hole parts", f"{c['tht']} ({c['n_tht']} parts): hand or selective soldering, seated flat"],
    ["Cleaning", "<b>please wash off the flux</b> (IPA or aqueous) and dry. The thermocouple inputs are "
                 "high-impedance; flux residue in the area marked ISOLATED SENSOR SIDE becomes a measurement error"]])}

<h2>5. Orientation checklist</h2>
{table(["Reference", "Part", "Check"], ORIENT)}

<h2>6. Not fitted by you</h2>
<p>{("Please leave these footprints empty (not in the BOM or CPL): " + dnp + ". ") if dnp else
   "Every footprint on the board is fitted, including the RS-485 block (U703, J703) and the headers JP731-JP733 (no jumper shunts: they are set at the site). "}
{text.get('programming', 'Please do <b>not</b> fit the LCD module and do <b>not</b> program the microcontroller: we do both.')}</p>

<h2>7. Accuracy parts</h2>
<p>{text.get('accuracy', 'AD7124-8, TMP126, BAV199, the 20M and 1 % resistors and the C0G capacitors set the measurement' + chr(10) + 'accuracy. If one of them is hard to get, we would be grateful for a word before an alternative is used.')}</p>

<h2>8. Power-on test (please quote it as an option)</h2>
<p>{text.get('power_setup', 'No firmware is needed.')} Supply <b>24.0 V</b> with the current limit set to <b>{text.get('current_limit', '150 mA')}</b> on J601
{text.get('power_pins', '(+24V and 0V)')}, nothing else connected. Measure with a multimeter. The isolated side has its own
ground: measure each point against the ground named in the table, <b>GND ({REF_TP['GND']})</b> or <b>GNDI ({REF_TP['GNDI']})</b>.</p>
{table([text.get('measurement_label', "Test point (silkscreen)"), "Measure against", "Expected", "Set by"], tests)}
<p>Also record: <b>input current</b> at 24 V ({text.get('current_record', 'normal is well below 100 mA; the boards should agree with each' + chr(10) + 'other within about 20 %')}), and, <b>with power off</b>, the resistance from GND ({REF_TP['GND']}) to GNDI ({REF_TP['GNDI']}):
the meter must show <b>open</b> (above 10 Mohm). A board outside any range: please stop and tell us.</p>
<p>{text.get('point_map', 'Where the points are: see the <b>test-point map on the last page</b>.')}</p>

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
<li>Full function: all {P['channels']} thermocouple channels read{text.get('function_extra', '')}, the trip and alarm relays switch.</li>
</ol>
<p>A fault that traces back to assembly we would like to return to you for rework.</p>

<h2>11. Optional: conformal coating</h2>
<p>If you offer it: acrylic conformal coating (IPC-CC-830 type), both sides, <b>after</b> washing and
testing, with connectors, pin headers, buttons, relays, test points and the LCD header masked.
If not, we will do it ourselves.</p>

<h2>12. Accessories (ACCESSORIES.csv)</h2>
<p>{text.get('accessories', 'Mating plugs 3.81 mm 8-pin x6 and 2-pin x1, XH 6-pin housing with contacts, LCD 16-pin socket,' + chr(10) + '2.54 mm jumper shunts x3 (loose, for JP731-JP733),' + chr(10) + 'M3 x 10 standoffs. If you also have the 3.81 mm plugs and headers in other colours, please quote them.')}</p>
"""
P24["assembly_html"] = assembly24_html
def order24_notes(pcb, name, board_size, P=None, accuracy=None):
    P = P24 if P is None else P
    return f"""REQUEST FOR QUOTATION - Thermo {P['channels']}-channel board ({name})
Board size {board_size(pcb)}, {P.get('copper_layers', 4)} layers. Quantity: please quote 5 and 10 boards.

Hello, and thank you for looking at this. We would like a quotation for the bare boards and for
assembly. Everything below is our preferred build; if you work differently or suggest a better or
cheaper option, please tell us - we are glad to discuss it.

FILES
- {P['project']}-gerbers.zip : Gerbers + drill ({P.get('copper_layers', 4)} copper layers).
- BOM.csv              : parts list. The LCSC column is a reference part number only - you can source
                         the parts wherever suits you; equivalents are welcome.
- CPL.csv              : placement list (all parts on the top side).
- DNP.txt              : footprints that stay empty on this order (not in the BOM or CPL).
- ACCESSORIES.csv      : loose items (mating plugs, standoffs). Please quote them if you can supply them.
- ASSEMBLY-SPEC.pdf    : the full build preferences, the power-on test with expected values, and
                         what we would like back with the boards.

PCB (preferred)
- FR4, 1.6 mm, 1 oz copper on all layers, ENIG finish (several fine-pitch and exposed-pad parts).
- Vias covered by solder mask (tented).{(chr(10) + '- ' + P['fab_limits']) if P.get('fab_limits') else ''}

ASSEMBLY (preferred)
- Stencil and reflow for the SMD parts. {P.require('exposed_pad_text')} have an
  exposed pad underneath that must be soldered; the paste layer in the Gerbers already has the openings.
- The green screw terminals J601, J701, J702, J703 face outward: the wire entry is toward the board edge,
  as drawn on the silkscreen (the part fits either way round, so please check this one).
- Please wash off the flux after soldering. Several inputs are high-impedance, and flux residue there
  turns into a measurement error.
{accuracy if accuracy is not None else '- A few parts set the measurement accuracy: AD7124-8, TMP126, BAV199, the 20M and 1% resistors and the' + chr(10) + '  C0G capacitors. If one of them is hard to get, we would appreciate a word before an alternative is used.'}

OPTIONAL - CONFORMAL COATING
If you offer it, please quote acrylic conformal coating after testing (IPC-CC-830 type, both sides),
with the connectors, pin headers, buttons, relays and the LCD header masked. If not, we will do it.

In the quotation it would help us to see: PCB price, assembly price, parts price, lead time, and
any part you could not find or would replace. Thank you.
"""
P24["order_notes"] = order24_notes

def select():
    key, pcb = os.environ.get('THERMO_BOARD', '24'), None
    args, rest, i = sys.argv[1:], [], 0
    while i < len(args):
        flag, sep, val = args[i].partition('=')
        if flag in ('--board', '--pcb'):
            if not sep:
                i += 1
                if i == len(args):
                    raise SystemExit(f'{flag} requires a value')
                val = args[i]
            if flag == '--board':
                key = val
            else:
                pcb = val
        else:
            rest.append(args[i])
        i += 1
    if key not in PROFILES:
        raise SystemExit('--board must be 24, 8, 8l or 40 (copy path: --pcb)')
    sys.argv[1:] = rest
    os.environ['THERMO_BOARD'] = key
    p = PROFILES[key]
    prefix = 'THERMO' + key
    pcb = pcb or os.environ.get(prefix + '_BOARD')
    if pcb:
        os.environ[prefix + '_BOARD'] = str(Path(pcb).resolve())
    p['pcb'] = Path(pcb).resolve() if pcb else p['folder'] / (p['project'] + '.kicad_pcb')
    p['work_folder'] = p['pcb'].parent
    p['output'] = p['work_folder'] / 'output'
    p['netlist'] = p['pcb'].with_suffix('.xml')
    p['rules_file'] = p['folder'] / 'gen' / 'rules.py'
    return p
def geometry():
    """Read-only import: never run the per-board writer or fall back to 24-ch."""
    path = ACTIVE['rules_file']
    if not path.is_file():
        raise SystemExit(f'profile {ACTIVE["key"]}: {path}: set by floor plan')
    spec = importlib.util.spec_from_file_location('_floor_plan_rules', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.domain, module.BANDS

__import__('profiles_new').apply(PROFILES, P24)  # 8-ch / 40-ch data (Claude, 2026-10-14)
__import__('docs_new').apply(PROFILES, P24)  # 8-ch / 40-ch release texts (Sol, 2026-10-14)
ACTIVE = select()
