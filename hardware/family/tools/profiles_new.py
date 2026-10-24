"""8-ch and 40-ch board profiles (Claude, 2026-10-14): same nets, classes and rules as the 24-ch; geometry from each
board's gen/place.py floor plan v1. Silk, assembly and release text are set when those boards reach them.
"""
_P24 = {}

_SHARED = ('plane_nets', 'plane_domains', 'contact_nets', 'chassis_net', 'high_clearance_nets', 'keep_nets',
           'keep_prefix', 'classes', 'pair_rules', 'bias_net', 'island_prefix', 'bias_prefix', 'board_only',
           'bootstrap_nets')


def _pin_checks(adcs, isolators):
    return [c for c in _P24['pin_checks'] if c[0] in ('U601', 'U501')] + [
        (u, pin, 3.0, what) for u in isolators for pin, what in (('1', 'ISO7761 VCC1'), ('16', 'ISO7761 VCC2'))] + [
        (u, pin, lim, what) for u in adcs for pin, lim, what in (
            ('26', 'plane', 'AD7124 AVDD'), ('2', 'plane', 'AD7124 IOVDD'),
            ('24', 5.0, 'AD7124 REGCAPA'), ('1', 5.0, 'AD7124 REGCAPD'), ('22', 5.0, 'AD7124 REFOUT'))]


def apply(PROFILES, P24):
    _P24.update(P24)
    for _key in ('8', '40'):
        PROFILES[_key].update({k: P24[k] for k in _SHARED})
    PROFILES['8'].update(
        fiducials={'FID1': (10.0, 10.0), 'FID2': (120.0, 32.0), 'FID3': (10.0, 116.0)},
        fab_limits='track 0.20 mm; spacing 0.15 mm (AD7124 LFCSP 0.5 mm pitch); vias 0.6/0.3 mm (0.15 mm ring), smallest drill 0.3 mm',
        pin_checks=_pin_checks(('U101',), ('U403', 'U404')), release_prefix='8ch-revb0', silk=dict(
            P24['silk'], barriers=((0.5, 92.5, 129.5, 92.5), (101.5, 0.5, 101.5, 26.5), (101.5, 26.5, 129.5, 26.5)),
            horizontal=('J101', 'J102'), vertical=(), horizontal_y=125.3, isp_dy=8.0, terminal_y=12.0,
            bus_y=19.6, label_by_net=True,
            fixed=(('ENGINE REF: 1 FEED 2 SENSE', 91.0, 124.8, (0.6, 0.8), {'reach': 3.0}),
                   ('2 WIRES, JOINED ONLY AT THE ENGINE', 91.0, 123.4, (0.6, 0.8), {'reach': 3.0, 'must': False}),
                   ('K/J TC: n+ / n-', 30.0, 123.6, 0.9, {'reach': 6, 'must': False}),
                   ('CONTACTS: LOW-VOLTAGE SIGNAL LOAD ONLY, 30 VDC / 1 A MAX', 77.0, 26.0, (0.7, 0.8),
                    {'bold': True, 'reach': 6}),
                   ('THERMO 8-CH  REV B0', 115.0, 84.0, 1.5, {'bold': True, 'reach': 8}),
                   ('ISOLATED SENSOR SIDE', 20.0, 95.6, 1.0, {'reach': 5}))))
    p8l = type(PROFILES['8'])(PROFILES['8'])          # 2-layer REV B0-2L (0040): the 4-layer spread 1.154 x 1.124
    p8l.update(key='8l', project='thermo8', folder=PROFILES['8']['folder'].parent / '8ch-2l', revision='REV B0-2L',
               width=150.0, height=154.0, outline=((0, 0), (150, 0), (150, 154), (0, 154)),
               release_prefix='8ch-revb0-2l',
               copper_layers=2,
               fab_limits='track 0.20 mm; spacing 0.20 mm, 0.15 mm around the AD7124 (U101, LFCSP 0.5 mm pitch); '
                          'vias 0.7/0.3 mm, 23 at 0.6/0.3 mm (0.15 mm ring) where 0.7 does not fit',
               bias_keep_b=True,                # B.Cu GND_ISO is the only ground plane (vbias_pour)
               mounting_holes={'H5': (4.5, 4.5), 'H4': (146.0, 44.96), 'H6': (12.35, 36.57), 'H7': (105.35, 36.57),
                               'H8': (12.35, 91.57), 'H9': (105.35, 91.57), 'H1': (4.5, 149.5), 'H3': (145.5, 149.5),
                               'H2': (4.5, 112.41), 'H10': (103.85, 127.02)},
               fiducials={'FID1': (10.0, 10.0), 'FID2': (140.0, 36.0), 'FID3': (10.0, 133.0)},
               silk=dict(PROFILES['8']['silk'],
                         barriers=((0.5, 104.0, 149.5, 104.0), (121.5, 0.5, 121.5, 29.8), (121.5, 29.8, 149.5, 29.8)),
                         horizontal_y=142.3,
                         fixed=(('ENGINE REF: 1 FEED 2 SENSE', 102.7, 141.8, (0.6, 0.8), {'reach': 3.0}),
                                ('2 WIRES, JOINED ONLY AT THE ENGINE', 102.7, 140.4, (0.6, 0.8),
                                 {'reach': 3.0, 'must': False}),
                                ('K/J TC: n+ / n-', 40.0, 140.6, 0.9, {'reach': 6, 'must': False}),
                                ('CONTACTS: LOW-VOLTAGE SIGNAL LOAD ONLY, 30 VDC / 1 A MAX', 88.9, 29.2, (0.7, 0.8),
                                 {'bold': True, 'reach': 6}),
                                ('THERMO 8-CH  REV B0-2L', 132.7, 94.4, 1.5, {'bold': True, 'reach': 8}),
                                ('ISOLATED SENSOR SIDE', 23.0, 107.5, 1.0, {'reach': 5}))))
    p8l['pin_checks'] = [(u, pin, 4.5 if (u, pin) in (('U501', '5'), ('U404', '16')) else lim, what)
                         for u, pin, lim, what in p8l['pin_checks']]   # spread placement: 3.9 / 4.0 mm (0040)
    PROFILES['8l'] = p8l
    PROFILES['40'].update(
        width=250.0, height=145.0, outline=((0, 0), (250, 0), (250, 145), (0, 145)), revision='REV A0',
        bank_channels=(8, 8, 8, 8, 8), buck_ref='U601', release_prefix='40ch-reva0',
        fab_limits='track 0.20 mm; spacing 0.15 mm (AD7124 LFCSP 0.5 mm pitch); vias 0.6/0.3 mm (0.15 mm ring), smallest drill 0.3 mm',
        mounting_holes={'H1': (4.5, 140.5), 'H2': (4.5, 101), 'H3': (245.5, 140.5), 'H4': (165.5, 92),
                        'H5': (165.5, 4.5), 'H10': (4.5, 4.5), 'H6': (49.5, 41.5), 'H7': (142.5, 41.5),
                        'H8': (49.5, 96.5), 'H9': (142.5, 96.5)},
        fiducials={'FID1': (10.0, 10.0), 'FID2': (190.0, 12.0), 'FID3': (10.0, 135.0)},
        silk=dict(P24['silk'], label_by_net=True,
                  barriers=P24['silk']['barriers'][:1] + ((43.5, 101.5, 196.5, 101.5), (196.5, 101.5, 196.5, 0.5))
                  + P24['silk']['barriers'][2:],
                  horizontal=('J101', 'J102', 'J201', 'J202', 'J301', 'J302'), vertical=('J801', 'J802', 'J901', 'J902'),
                  vertical_x={'J901': (238.6, 238.7), 'J902': (238.6, 238.7)},   # bank E: right edge
                  terminal_y_at={'J1001': (5.6, 2.6), 'J1002': (5.6, 2.6)},   # PT100: 2512 parts right under the pins
                  terminals=P24['silk']['terminals'] + (('J1001', (), 'PT100 1-2'), ('J1002', (), 'PT100 3')),
                  fixed=P24['silk']['fixed'][:2] + (('K/J TC: n+ / n-', 30.0, 131.0, 0.9, {'reach': 6, 'must': False}),)
                  + P24['silk']['fixed'][3:4] + (('THERMO 40-CH  REV A0', 106.0, 84.0, 1.5, {'bold': True, 'reach': 6}),)
                  + P24['silk']['fixed'][5:]),
        pin_checks=_pin_checks(('U101', 'U201', 'U301', 'U801', 'U901', 'U1001'), ('U403', 'U404')))
