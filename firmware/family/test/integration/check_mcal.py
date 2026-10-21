"""Focused target-cycle regressions, run after profile_avr.ps1."""
from pathlib import Path
import re
import sys
text = Path(sys.argv[1], "mcal.log").read_text()
samples = {}
for kind, _, start, end in re.findall(
        r"BEGIN (\d+) (\d+)\n.*?# cycles\s+(\d+)\n.*?END\n.*?# cycles\s+(\d+)", text, re.S):
    samples.setdefault(int(kind), []).append(int(end)-int(start))
assert len(samples[9]) == 256
print(f"Soft SPI cycles/byte: {max(samples[9])}")
assert max(samples[9]) <= 512, "Software SPI still calls generic GPIO/delay loops"
if "--keys" in sys.argv:
    print(f"Timer2 ISR cycles: {max(samples[32])}")
    assert max(samples[32]) <= 250, "Timer2 ISR exceeds its cycle budget"
