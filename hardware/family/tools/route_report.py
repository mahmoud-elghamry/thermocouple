"""Report profiled sense pairs, Kelvin/stars or arbitrary --path/--shared pads.

Run with KiCad Python and --board. No flags: profiled pairs/stars/Kelvin.
--path A.1 B.2 may repeat; --shared COMMON.1 SENSE.1 CURRENT.1 may repeat.
Custom requests replace the profile's defaults. Exit 2 means invalid or missing
routes; this metric report deliberately imposes no unrequested length limits.
"""
import argparse
from audit_common import emit, load_board, selected_board
from route_graph import shared_length
from route_native import BoardRoutes


def measure(board, profile, paths=(), shared=()):
    routes = BoardRoutes(board)
    pairs, runs, explicit = [], [], []

    def common_run(common, sense, branch):
        first, second = routes.path(common, sense), routes.path(common, branch)
        value = None
        if first['length_mm'] is not None and second['length_mm'] is not None:
            value = shared_length(first['path'], second['path'], routes.outside(common))
        return dict(common=common, sense=first, branch=second, shared_outside_pad_mm=value)

    if paths or shared:
        explicit = [routes.path(*endpoints) for endpoints in paths]
        runs = [common_run(*endpoints) for endpoints in shared]
    else:
        for name, endpoints in profile['route_pairs']:
            legs = [routes.path(*ends) for ends in endpoints]
            lengths = [leg['length_mm'] for leg in legs]
            pairs.append(dict(name=name, legs=legs, mismatch_mm=None if None in lengths
                              else abs(lengths[0]-lengths[1])))
        runs = [common_run(*ends) for ends in profile['route_stars']]
        for common, sense in profile['route_kelvin']:
            net = routes.pads[common].GetNetname()
            branches = [label for label, pad in routes.pads.items()
                        if pad.GetNetname() == net and label not in (common, sense)]
            runs.extend(common_run(common, sense, branch) for branch in branches)
    measured = explicit + [leg for pair in pairs for leg in pair['legs']]
    measured += [leg for run in runs for leg in (run['sense'], run['branch'])]
    return dict(convention='shortest centreline, pad-centre projections, no pours',
                pairs=pairs, paths=explicit, shared_runs=runs,
                disconnected_paths=sum(x['length_mm'] is None for x in measured))


def main():
    profile = selected_board()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', nargs=2, action='append', default=[])
    parser.add_argument('--shared', nargs=3, action='append', default=[])
    args = parser.parse_args()
    try:
        result = measure(load_board(profile), profile, args.path, args.shared)
    except (KeyError, ValueError) as exc:
        parser.error(str(exc))
    emit(profile, result)
    return 2 if result['disconnected_paths'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
