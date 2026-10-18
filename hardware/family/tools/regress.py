"""Orchestrator-only original/family checks. All writes stay in tools-test/<run>."""
import ctypes
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from regress_compare import compare_file, compare_tree, normal_text, tree_hashes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DONOR = ROOT / 'hardware' / '24ch'
KPY = Path(r'C:\Program Files\KiCad\10.0\bin\python.exe')
CLI = Path(r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe')
SCRATCH = HERE.parent / 'tools-test' / datetime.datetime.now().strftime('regress-%Y%m%d-%H%M%S-%f')
RESULTS = []


def record(name, ok, reason, **detail):
    RESULTS.append(dict(name=name, ok=ok, reason=reason, **detail))
    prefix = 'PASS (same failure as original) ' if ok and reason == 'same failure as original' else 'PASS ' if ok else 'FAIL '
    print(prefix + name + ': ' + reason, flush=True)


def run(cmd, log, env=None, accepted=(0,), timeout=600):
    settings = os.environ.copy()
    # Do not inherit an owner's work-copy/release/claim selection.
    for key in list(settings):
        if key.startswith('THERMO'):
            del settings[key]
    settings.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8',
                    KICAD_CLI=str(CLI), KICAD_PYTHON=str(KPY))
    settings.update(env or {})
    cmd = list(map(str, cmd))
    print('CMD ' + subprocess.list2cmdline(cmd), flush=True)
    started = time.monotonic()
    try:
        p = subprocess.Popen(cmd, env=settings, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding='utf-8', errors='replace', cwd=ROOT)
        try:
            stdout, stderr = p.communicate(timeout=timeout)
            code = p.returncode
        except subprocess.TimeoutExpired:
            # Kill only this harness-owned process tree; preserve diagnostics gathered so far.
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True)
            else:
                p.kill()
            stdout, stderr = p.communicate()
            stderr += f'\nHarness timeout after {timeout} seconds'
            code = -1
    except OSError as e:
        stdout, stderr, code = '', str(e), -1
    log.parent.mkdir(parents=True, exist_ok=True)
    log.with_suffix('.stdout').write_text(stdout, encoding='utf-8')
    log.with_suffix('.stderr').write_text(stderr, encoding='utf-8')
    log.with_suffix('.command.json').write_text(json.dumps(dict(command=cmd, exit=code, env=env or {},
                   elapsed_seconds=round(time.monotonic() - started, 3), timeout=timeout), indent=2), encoding='utf-8')
    return code in accepted, stdout, stderr, code


def fixture(name):
    path = SCRATCH / name
    path.mkdir()
    for p in DONOR.iterdir():
        if p.is_file() and (p.suffix in ('.kicad_pcb', '.kicad_pro', '.kicad_dru', '.kicad_sch', '.csv')
                           or p.name in ('sym-lib-table', 'fp-lib-table')):
            shutil.copy2(p, path / p.name)
    shutil.copytree(DONOR / 'lib', path / 'lib')
    # Exact donor scripts, including untouched per-board rules.py, in scratch only.
    (path / 'gen').mkdir()
    for p in (DONOR / 'gen').glob('*.py'):
        shutil.copy2(p, path / 'gen' / p.name)
    (path / 'output').mkdir()
    return path


def env(path):
    return {'THERMO24_BOARD': str(path / 'thermo24.kicad_pcb'),
            'THERMO24_WRITER_CLAIM': str(path / 'output' / '.writer.json')}


def pair(name, a, b, args=(), mode=None, accepted=(0,), timeout=600):
    original = a / 'gen' / (name + '.py')
    family = HERE / (name + '.py')
    ca = [KPY, '-B', original, *args]
    cb = [KPY, '-B', family, '--board', '24', '--pcb', b / 'thermo24.kicad_pcb', *args]
    if mode:
        ca = [KPY, '-B', HERE / 'regress_worker.py', mode, original, *args]
        cb = [KPY, '-B', HERE / 'regress_worker.py', mode, family,
              '--board', '24', '--pcb', b / 'thermo24.kicad_pcb', *args]
        if mode == 'cost':
            # Worker consumes the shared fixture before the common board selectors.
            cb = [KPY, '-B', HERE / 'regress_worker.py', mode, family, args[0],
                  '--board', '24', '--pcb', b / 'thermo24.kicad_pcb', *args[1:]]
    ra = run(ca, a / 'output' / ('log-' + name + '-original'), env(a), accepted, timeout)
    rb = run(cb, b / 'output' / ('log-' + name + '-family'), env(b), accepted, timeout)
    ok = ra[0] and rb[0] and ra[3] == rb[3] and normal_text(ra[1], (a, b)) == normal_text(rb[1], (a, b))
    return ok, dict(original=ca, family=cb, exits=(ra[3], rb[3]), stdout=(ra[1], rb[1]), stderr=(ra[2], rb[2]))


def same_failure(exits, stdout, hashes):
    return 0 < exits[0] < 126 and exits[0] == exits[1] and stdout[0] == stdout[1] and hashes[0] == hashes[1]


def repaired_check(name, a, b, detail):
    # This is explicitly a repaired reference, not equivalence to the failing CLI.
    signature = 'holds the writer claim' if name == 'silk' else "'SwigPyObject' object has no attribute 'Pads'"
    if detail['exits'] != (1, 0) or signature not in detail['stderr'][0]:
        return False, 'unexpected original/family failure', {}
    command = [KPY, '-B', HERE / 'regress_worker.py', 'reference-fixed', a / 'gen' / (name + '.py')]
    result = run(command, a / 'output' / ('log-' + name + '-repaired-reference'), env(a))
    same, why, hashes = compare_file(a / 'thermo24.kicad_pcb', b / 'thermo24.kicad_pcb')
    ok = result[0] and normal_text(result[1], (a, b)) == normal_text(detail['stdout'][1], (a, b)) and same
    return ok, 'family fixes donor bug; repaired reference: ' + why, dict(reference_command=command,
                  reference_exit=result[3], reference_stderr=result[2], sha256=hashes)


def read_checks(a):
    for name, args, accepted in (
            ('padcheck', (), (0,)), ('pincaps', (), (0, 1)),
            ('guard', (str(a / 'thermo24.kicad_pcb'),), (0,)),
            ('capnear', ('U403', '1', 'C407', '--step', '0.5', '--show', '5'), (0, 2)),
            ('delta', ('--dry',), (0,))):
        if name == 'delta' and not (a / 'thermo24.xml').exists():
            record('delta stdout', False, 'netlist fixture unavailable')
            continue
        ok, detail = pair(name, a, a, args, accepted=accepted)
        record(name + ' stdout', ok, 'exact stdout + matching exits on the same copy', **detail)
    if not (a / 'thermo24.xml').exists():
        record('cost stdout/CSV', False, 'netlist fixture unavailable')
    else:
        cost_check(a)
    for name in ('maze', 'route24', 'fanout'):
        ok, detail = pair(name, a, a, mode='constants')
        record(name + ' constants', ok, 'same resolved constants; no router/export/save invoked', **detail)


def cost_check(a):
    prices = SCRATCH / 'prices.json'
    refs = {f.text for c in ET.parse(a / 'thermo24.xml').getroot().iter('comp')
            for f in c.iter('field') if f.get('name') == 'LCSC' and f.text}
    prices.write_text(json.dumps({code: dict(mfr='REGRESSION-' + code, price=(i + 1) / 100,
                  stock=i * 5, is_basic=i % 2 == 0) for i, code in enumerate(sorted(refs))}), encoding='utf-8')
    b = fixture('cost-B')
    shutil.copy2(a / 'thermo24.xml', b / 'thermo24.xml')
    ok, detail = pair('cost', a, b, (str(prices), '5'), mode='cost')
    if not (a / 'output' / 'cost.csv').exists() or not (b / 'output' / 'cost.csv').exists():
        record('cost stdout/CSV', False, 'cost failed to produce CSV', **detail)
        csv_ok, why, hashes = False, 'CSV missing', ()
    else:
        csv_ok, why, hashes = compare_file(a / 'output' / 'cost.csv', b / 'output' / 'cost.csv')
    record('cost stdout/CSV', ok and csv_ok, 'shared offline prices; ' + why, sha256=hashes, **detail)


def write_checks(base):
    checks = [('silk', ()), ('fiducials', ()), ('vbias_pour', ()), ('fanout', ()),
              ('move', ('C407', '68.2', '90.0', '90')), ('delta', ()),
              ('finish', ('lock',)), ('finish', ('unlock',)),
              ('finish', ('unlock-box', '0', '0', '20', '20')),
              ('finish', ('strip', 'REGCAPA_A')), ('finish', ('dedupe',)),
              ('finish', ('drc',)), ('finish', ('stubs',)), ('finish', ('nori',)), ('finish', ('dangling',)),
              ('finish', ('rip',)), ('finish', ('add', 'GND', 'F.Cu', '0.25', '150,80', '151,80', 'via')),
              ('pcb_new', ('--force',))]
    for i, (name, args) in enumerate(checks):
        a, b = fixture(f'write-{i}-A'), fixture(f'write-{i}-B')
        if name == 'delta' and not (base / 'thermo24.xml').exists():
            record('delta write', False, 'netlist fixture unavailable')
            continue
        for p in (a, b):
            if (base / 'thermo24.xml').exists():
                shutil.copy2(base / 'thermo24.xml', p / 'thermo24.xml')
            # Fresh report input for nori/rip; all other report-using operations run DRC.
            (p / 'output' / 'finish-drc.json').write_text(json.dumps({'violations': [], 'unconnected_items': []}), encoding='utf-8')
            (p / 'output' / 'maze-rip.txt').write_text('', encoding='utf-8')
        ok, detail = pair(name, a, b, args, accepted=(0, 1), timeout=3600 if args == ('dangling',) else 600)
        same, why, hashes = compare_file(a / 'thermo24.kicad_pcb', b / 'thermo24.kicad_pcb')
        if same_failure(detail['exits'], detail['stdout'], hashes):
            record(name, True, 'same failure as original', sha256=hashes, **detail)
        elif name in ('silk', 'fiducials') and detail['exits'] != (0, 0):
            ok, why, reference = repaired_check(name, a, b, detail)
            record(name, ok, why, **reference, **detail)
        else:
            record(name + ' ' + ' '.join(args), ok and same and detail['exits'] == (0, 0), why, sha256=hashes, **detail)


def view_checks():
    a, b = fixture('view-A'), fixture('view-B')
    results = []
    commands = []
    for p, script in ((a, a / 'gen/view.py'), (b, HERE / 'view.py')):
        cmd = [sys.executable, '-B', script, '0', '0', '40', '30', p / 'view.png']
        if script.parent == HERE:
            cmd += ['--board', '24', '--pcb', p / 'thermo24.kicad_pcb']
        commands.append(cmd)
        results.append(run(cmd, p / 'output/log-view', env(p)))
    if all(r[0] for r in results) and (a / 'view.png').exists() and (b / 'view.png').exists():
        same, why, hashes = compare_file(a / 'view.png', b / 'view.png')
        record('view', same, why, sha256=hashes, commands=commands)
    else:
        record('view', False, 'render/PyMuPDF dependency failed', commands=commands, stderr=[r[2] for r in results])


def fab_checks():
    a, b = fixture('fab-A'), fixture('fab-B')
    paths = []
    outputs = []
    for label, path, script in (('A', a, a / 'gen' / 'fab.py'), ('B', b, HERE / 'fab.py')):
        out = path / 'release'
        settings = env(path) | {'THERMO24_FAB_PCB': str(path / 'thermo24.kicad_pcb'),
                               'THERMO24_FAB_SCH': str(path / 'thermo24.kicad_sch'), 'THERMO24_FAB_OUT': str(out)}
        cmd = [sys.executable, '-B', script]
        if label == 'B':
            cmd += ['--board', '24', '--pcb', path / 'thermo24.kicad_pcb']
        result = run(cmd, path / 'output' / 'log-fab', settings)
        outputs.append(result)
        folders = list(out.glob('*')) if out.exists() else []
        paths.append(folders[0] if len(folders) == 1 and result[0] else None)
    if not all(paths):
        record('fab', False, 'release gate failed; see full stderr/logs', exits=[r[3] for r in outputs], stderr=[r[2] for r in outputs])
        return
    comparisons = compare_tree(*paths)
    record('fab', all(c['ok'] for c in comparisons), 'every release file compared', files=comparisons)
    # Additional tool gate: assembler PDF from the matching release and PCB copy.
    for path, release, script in ((a, paths[0], a / 'gen' / 'assembly_spec.py'), (b, paths[1], HERE / 'assembly_spec.py')):
        cmd = [sys.executable, '-B', script, release]
        if script.parent == HERE:
            cmd += ['--board', '24', '--pcb', path / 'thermo24.kicad_pcb']
        result = run(cmd, path / 'output' / 'log-assembly', env(path))
        if not result[0]:
            record('assembly_spec', False, 'tool failed', stderr=result[2])
            return
    same, why, hashes = compare_file(paths[0] / 'ASSEMBLY-SPEC.pdf', paths[1] / 'ASSEMBLY-SPEC.pdf', (paths[0], paths[1]), (paths[0].name, paths[1].name))
    record('assembly_spec', same, why, sha256=hashes)


def main():
    if os.name == 'nt':
        ctypes.windll.kernel32.SetErrorMode(0x8003)
    SCRATCH.mkdir(parents=True)
    before = tree_hashes(DONOR)
    (SCRATCH / 'source-before.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
    try:
        result = run([sys.executable, '-B', HERE / 'test_profiles.py'], SCRATCH / 'pure')
        record('pure checks', result[0], 'profile/AST/guard/geometry tests', stderr=result[2])
        a = fixture('read-A')
        result = run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', a / 'thermo24.xml', a / 'thermo24.kicad_sch'], SCRATCH / 'netlist')
        record('netlist fixture', result[0] and (a / 'thermo24.xml').is_file(), 'scratch schematic -> XML', stderr=result[2])
        for name, fn in (('read checks', lambda: read_checks(a)), ('write checks', lambda: write_checks(a)), ('view checks', view_checks), ('fab checks', fab_checks)):
            try:
                fn()
            except Exception as e:
                record(name, False, f'{type(e).__name__}: {e}')
    except Exception as e:
        record('gate setup', False, f'{type(e).__name__}: {e}')
    finally:
        record('hardware/24ch byte identity', before == tree_hashes(DONOR), 'all files SHA256 + file set')
        (SCRATCH / 'summary.json').write_text(json.dumps(RESULTS, indent=2, default=str), encoding='utf-8')
    failed = sum(not r['ok'] for r in RESULTS)
    print(f'REGRESS: {len(RESULTS) - failed} passed, {failed} failed; evidence: {SCRATCH}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
