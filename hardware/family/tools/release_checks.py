"""Pure report validation shared by fabrication and copy-only coordination tools."""
from collections import Counter
import re

BLOCKERS = ('track_dangling', 'via_dangling')


def copper_layers(count):
    if count not in (2, 4):
        raise ValueError(f'unsupported copper stack: {count}')
    return ('F.Cu', 'B.Cu') if count == 2 else ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')


def warning_summary(text):
    """Require a complete all-severity report; never accept disconnected copper."""
    patterns = ('DRC violations', 'unconnected pads', 'Footprint errors')
    counts = []
    for label in patterns:
        match = re.search(r'\*\* Found (\d+) ' + label, text)
        if not match:
            raise ValueError(f'incomplete DRC report: missing {label}')
        counts.append(int(match[1]))
    kinds = dict(sorted(Counter(re.findall(r'^\[([a-z_]+)\]', text, re.M)).items()))
    if sum(kinds.values()) != counts[0] + counts[2]:
        raise ValueError('DRC violation count does not match listed findings')
    if counts[1] or re.search(r';\s*error\b', text):
        raise ValueError('all-severity DRC has errors or unconnected pads')
    bad = {kind: kinds[kind] for kind in BLOCKERS if kinds.get(kind)}
    if bad:
        raise ValueError(f'dangling copper blocks release: {bad}')
    return kinds
