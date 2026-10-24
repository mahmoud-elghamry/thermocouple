"""8/40 release text, using 0039, fitted BOMs and CALCULATIONS 9/10.

Pure Python: never import the fabrication or KiCad entry points. The power-on test
uses the 24-ch test points: same circuit, same refs and nets on both boards (bare
pads, so they are not in BOM.csv).
Power budgets are screening estimates, not measured acceptance limits.
"""
import copy
import csv
from functools import partial
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
REF = re.compile(r'\b(?:JP|SW|RV|[CRDUJKQYLF])\d{2,4}\b')


def _number(ref):
    return (ref.rstrip('0123456789'), int(re.search(r'\d+$', ref).group()))


def _bom(folder):
    with (folder / 'BOM.csv').open(encoding='utf-8-sig', newline='') as f:
        return {ref.strip(): row for row in csv.DictReader(f) for ref in row['Designator'].split(',')}


def _parts(bom, mpn):
    return sorted((ref for ref, row in bom.items() if row['MPN'] == mpn), key=_number)


def _assembly(donor, bom, adcs, cjs):
    orient = []
    for refs, part, check in donor['ORIENT']:
        if part.startswith('AD7124'):
            refs = ', '.join(adcs)
        elif part.startswith('TMP126'):
            refs = ', '.join(cjs)
        elif part == '3.81 mm pluggable headers':
            refs = ', '.join(sorted((r for r, row in bom.items() if r.startswith('J')
                                    and 'PhoenixContact_MC' in row['Footprint']), key=_number))
        else:
            found = REF.findall(refs)
            fitted = [r for r in found if r in bom]
            refs = refs if fitted == found else ', '.join(fitted)
        if refs:   # the family boards have no milled slot, only a copper-free band (Astra 2026-10-16)
            orient.append((refs, part, check.replace('isolation slot', 'copper-free isolation gap')))
    orient.append(('U411', '74LVC1G125, SOT-23-5', 'pin-1 mark; gated TMP126 SIO command driver'))
    if 'U410' in bom:
        orient.append(('U410', '74HC154, TSSOP-24', 'pin-1 mark; island chip-select decoder'))
    orient.append(('J501, J502, J503', 'ISP, LCD and panel-button headers', 'pin 1 to the marked pad'))
    # the power circuit and its test points (TP401-407, TP501, TP601-603) are the 24-ch's, same refs and nets
    return dict(TESTS=donor['TESTS'], REF_TP=donor['REF_TP'], ORIENT=orient, LABEL_AT={})


def _accessories(bom, tc):
    plugs = [f'8-pin x{len(tc)}', '2-pin x1 (J401)']
    for pins in (6, 3):
        refs = sorted((r for r, row in bom.items() if r.startswith('J')
                       and 'PhoenixContact_MC' in row['Footprint']
                       and f'_1x0{pins}_' in row['Footprint']), key=_number)
        if refs:
            plugs.append(f'{pins}-pin x{len(refs)} ({", ".join(refs)})')
    shunts = sorted((r for r in bom if r.startswith('JP')), key=_number)
    return (f'Mating plugs 3.81 mm {", ".join(plugs)}; TC headers {", ".join(tc)}. '
            'XH 6-pin housing with six contacts x1 (J503); LCD 16-pin socket x1 (J502). '
            f'2.54 mm jumper shunts x{len(shunts)} (loose, for {", ".join(shunts)}). '
            'M3 LCD standoffs x4 and M3 board standoffs with screws (counts and lengths in ACCESSORIES.csv). '
            'If you have the plugs and headers in other colours, please quote them.')


def _texts(key, ep, accessories):
    section, typ = ('9.3', '69.2') if key.startswith('8') else ('10.3', '70.5')
    accuracy = ('AD7124-8, TMP126, BAV199, the 20M and 1 % resistors and C0G capacitors '
                'set the measurement accuracy. ')
    if key == '40':
        accuracy += ('The 3 PT100 inputs share U1001 with the on-board check slot. '
                     'PT100 reference R1092 is 2.49k 0.1 % 25 ppm/K; check resistor R1095 is 150R 0.1 %. '
                     'Keep the RTD reference Kelvin connections and wash the RTD sense networks. ')
    accuracy += 'Please ask before substituting any accuracy part.'
    return dict(
        exposed_pads=ep + ' have pads underneath that must be soldered. X-ray check preferred; '
                     'power-on readings alone do not establish exposed-pad solder quality.',
        programming='Please do <b>not</b> fit the LCD module (we mount it on standoffs) and do <b>not</b> '
                    'program the microcontroller: we do both.',
        accuracy=accuracy, accessories=accessories,
        current_record=f'normal is well below 100 mA (estimate, CALCULATIONS {section}: {typ} mA typical with '
                       'everything running); the boards should agree with each other within about 20 %',
        function_extra='' if key.startswith('8') else ' and all 3 PT100 inputs plus the on-board 150R check read',
    )


def apply(PROFILES, P24):
    """Register board-specific assembly tables and compatible four/three-arg renderers."""
    for key, folder, rev, width, height in (
            ('8', '8ch-new', 'REV B0', 130.0, 137.0), ('8l', '8ch-2l', 'REV B0-2L', 150.0, 154.0),
            ('40', '40ch', 'REV A0', 250.0, 145.0)):
        if key not in PROFILES:
            continue
        p = PROFILES[key]
        defaults = dict(project='thermo8' if key == '8l' else 'thermo' + key,
                        channels=int(key.rstrip('l')), revision=rev, width=width, height=height,
                        copper_layers=2 if key == '8l' else 4,
                        release_prefix={'8': '8ch-revb0', '8l': '8ch-revb0-2l', '40': '40ch-reva0'}[key],
                        folder=ROOT / 'hardware' / folder)
        p.update({k: v for k, v in defaults.items() if p.get(k) is None})
        bom = _bom(p['folder'])
        adcs, cjs = _parts(bom, 'AD7124-8BCPZ'), _parts(bom, 'TMP126DCKR')
        tc = sorted((r for r, row in bom.items() if row['Comment'].startswith('TC CH')), key=_number)
        if len(tc) * 4 != p['channels'] or len(adcs) != (1 if key.startswith('8') else 6):
            raise ValueError(f'profile {key}: BOM channel/ADC counts disagree')
        ep = f'The AD7124-8 ({", ".join(adcs)}; 5x5 mm LFCSP) and LM5164 (U601)'
        p['assembly'] = _assembly(copy.deepcopy(P24['assembly']), bom, adcs, cjs)
        text = _texts(key, ep, _accessories(bom, tc))
        p['assembly_html'] = partial(P24['assembly_html'], P=p, text=text)
        p['exposed_pad_text'] = ep
        p['order_notes'] = partial(P24['order_notes'], P=p, accuracy='- ' + text['accuracy'])
