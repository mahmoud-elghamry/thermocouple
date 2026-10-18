"""Child-only regression adapters: never change donor algorithms or invoke routers."""
import contextlib
import ast
import importlib.util
import io
import json
import os
import runpy
import sys
from pathlib import Path


def load(path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def constants(path):
    module = load(path)
    if path.stem == 'route24':
        # Exercise both CLI default pair-rule branches without DSN/Java/SES.
        module.export_dsn = module.import_ses = lambda: None
        module.run = lambda *args: None
        with contextlib.redirect_stdout(io.StringIO()):
            module.main()
        data = {k: getattr(module, k) for k in ('PAD', 'MIN_TRACK_MM', 'CLASS_CLASS')}
        data['names'] = [module.DSN.name, module.SES.name, module.LOG.name]
    elif path.stem == 'maze':
        data = {k: getattr(module, k) for k in ('W', 'H', 'NX', 'NY', 'RES', 'LAYERS',
                 'VIA_D', 'VIA_DR', 'VIA_COST', 'IN2_PENALTY', 'CONTACT', 'PLANE', 'KEEP', 'KEEP_PREFIX')}
        data['domain'] = [module.domain(x, y) for x in (0, 43, 56, 88, 169) for y in (0, 12, 24, 101, 144)]
        data['bands'] = module.BANDS
        data['clearance'] = [(a, b, module.need(a, b, pad, '')) for a in ('GND', 'TC1+', 'TRIP_NO', 'CHASSIS')
                             for b in ('TC2+', '+24V_RAW', 'TRIP_COM', '') for pad in (True, False)]
    elif path.stem == 'fanout':
        data = {k: getattr(module, k) for k in ('PLANE_NETS', 'CONTACT', 'VIA_D', 'VIA_DR', 'CLR', 'TRACK')}
        data['bands'] = module.BANDS
        # ADC tuple, formerly in three algorithm sites, is checked by pure AST tests too.
    else:
        raise ValueError(path)
    print(json.dumps(data, sort_keys=True, default=lambda v: sorted(v) if isinstance(v, set) else str(v)))


def offline_cost(path, prices):
    # Pricing is volatile/network-dependent; a shared explicit fixture proves grouping,
    # calculations, stock warnings and CSV parity, not current distributor prices.
    ns = runpy.run_path(str(path))
    fixture = json.loads(prices.read_text(encoding='utf-8'))
    ns['main'].__globals__['lookup'] = lambda code: fixture.get(code)
    ns['main'].__globals__['time'].sleep = lambda delay: None
    ns['main']()


def reference_fixed(path):
    """Only two documented donor bug corrections, in memory; donor files stay exact."""
    module = load(path)
    import guard
    tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    call = ast.parse('subprocess.run([sys.executable, _worker, "reference-strip", __file__], check=True)').body[0]
    if path.stem == 'silk':
        # Replace only its first child launch, which otherwise claims its parent's lock.
        index = next(i for i, n in enumerate(node.body) if isinstance(n, ast.Expr) and
                     isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'run')
        node.body[index] = call
    elif path.stem == 'fiducials':
        # Replace only the in-process FID removal by a fresh child, before LoadBoard.
        index = next(i for i, n in enumerate(node.body) if isinstance(n, ast.For))
        del node.body[index]
        node.body.insert(0, call)
    else:
        raise ValueError('unsupported reference correction')
    module.__dict__.update(_worker=str(Path(__file__).resolve()), subprocess=__import__('subprocess'), sys=sys)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), 'exec'), module.__dict__)
    with guard.claim(module.BOARD, path.name):
        module.main()


def reference_strip(path):
    module = load(path)
    import guard
    claim = guard.read_claim() or {}
    if (claim.get('pid') != os.getppid() or claim.get('tool') != path.name or
            Path(claim.get('board', '')).resolve() != Path(module.BOARD).resolve() or
            not guard.pid_alive(os.getppid()) or guard.kicad_locks(module.BOARD)):
        raise SystemExit('reference deletion child has no matching live parent claim')
    if path.stem == 'silk':
        module.strip()
    else:
        b = module.pcbnew.LoadBoard(module.BOARD)
        for f in [f for f in b.GetFootprints() if f.GetReference().startswith('FID')]:
            b.Remove(f)
        module.pcbnew.SaveBoard(module.BOARD, b)


if __name__ == '__main__':
    mode, target = sys.argv[1:3]
    path = Path(target).resolve()
    rest = sys.argv[3:]
    sys.argv = [str(path)] + rest
    sys.path.insert(0, str(path.parent))
    if mode == 'constants':
        constants(path)
    elif mode == 'cost':
        prices = Path(rest.pop(0))
        sys.argv = [str(path)] + rest
        offline_cost(path, prices)
    elif mode == 'reference-fixed':
        reference_fixed(path)
    elif mode == 'reference-strip':
        reference_strip(path)
    else:
        raise SystemExit('unknown worker mode')
