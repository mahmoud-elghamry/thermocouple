"""Measurement endpoints only: board-specific policy stays in profiles.* modules."""


def apply(profiles):
    for profile in profiles.values():
        profile.update(route_pairs=(), route_stars=(), route_kelvin=())
    p = profiles['40']
    adc = p['rtd_adc']
    p['route_pairs'] = tuple(
        (f'RTD{bank}', ((f'R10{bank}6.2', f'{adc}.{sp}'),
                       (f'R10{bank}8.2', f'{adc}.{sn}')))
        for bank, sp, sn in ((1, 6, 7), (2, 10, 11), (3, 16, 17), (4, 20, 21)))
    p['route_stars'] = tuple(
        (f'J100{1 if bank < 3 else 2}.{(bank-1)*3+offset if bank < 3 else offset}',
         f'R10{bank}{excitation}.1', f'R10{bank}{sense}.1')
        for bank in (1, 2, 3) for offset, excitation, sense in ((1, 1, 5), (2, 3, 7)))
    # The checker enumerates every other same-net pad as a current/cap branch.
    p['route_kelvin'] = (('R1092.1', f'{adc}.12'), ('R1092.2', f'{adc}.13'))
