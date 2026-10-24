"""Retain AVR simulator evidence and compare each UI call to 8000 cycles."""
import re
import subprocess
import sys
from pathlib import Path

gdb, commands, elf, report = sys.argv[1:]
result = subprocess.run([gdb, '-batch', '-x', commands, elf],
                        text=True, capture_output=True, timeout=60)
raw = result.stdout + result.stderr
Path(report).with_suffix('.raw.txt').write_text(raw, encoding='utf-8')
kind = None
begin = None
maxima = {}
end = False
for line in raw.splitlines():
    if line.startswith('BEGIN '):
        kind = int(line.split()[1])
        end = False
    elif line.startswith('END'):
        end = True
    elif line.startswith('# cycles'):
        cycles = int(re.findall(r'\d+', line)[0])
        if end and begin is not None:
            maxima[kind] = max(maxima.get(kind, 0), cycles - begin)
            begin = None
        else:
            begin = cycles
lines = [f'Case {k}: {v} cycles = {v/8000:.4f} ms' for k, v in sorted(maxima.items())]
lines.append(f'Calls profiled: {raw.count("BEGIN ")}')
text = '\n'.join(lines) + '\n'
Path(report).write_text(text, encoding='utf-8')
print(text)
sys.exit(0 if result.returncode == 0 and len(maxima) == 14 and max(maxima.values()) <= 8000 else 1)
