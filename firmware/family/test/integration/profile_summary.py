"""Report AVR instruction measurements separately from register-model CPU."""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
text = (root / "cycles.log").read_text()
mcal = (root / "mcal.log").read_text()
soft = [int(b)-int(a) for a,b in re.findall(
    r"BEGIN 9 \d+\n.*?# cycles\s+(\d+)\n.*?END\n.*?# cycles\s+(\d+)",mcal,re.S)]
assert len(soft)==256
marker = None
rows = []
start = fake = io_start = bound = 0
count = 0
# Conservative -Os MCAL bounds, including call/return margin. Soft SPI is
# calibrated across all 256 TX values in mcal.log (3234 cycles); reserve 3300.
costs = {1: 400, 2: 100, 3: 100, 4: 60, 6: 30, 7: 30, 8: 110,
         9: max(soft)+16, 10: 100, 11: 40, 12: 300, 13: 300, 14: 100,
         15: 40, 16: 60, 17: 20, 18: 80, 19: 100, 20: 10,
         21: 20, 22: 100, 23: 150, 24: 150, 25: 80, 26: 20,
         27: 100, 28: 100, 29: 100, 30: 80, 31: 60}
for line in text.splitlines():
    match = re.fullmatch(r"(BEGIN|END|IO_BEGIN|IO_END)(?: (.*))?", line)
    if match:
        marker = match[1], list(map(int, (match[2] or "").split()))
    match = re.match(r"# cycles\s+(\d+)", line.strip())
    if not match or not marker:
        continue
    kind, values = marker
    marker = None
    cycles = int(match[1])
    if kind == "BEGIN":
        start = cycles
        fake = bound = count = 0
    elif kind == "IO_BEGIN":
        io_start = cycles
        io, arg = values
        bound += 16 * arg + 40 if io == 5 else costs[io]
        count += 1
    elif kind == "IO_END":
        fake += cycles - io_start + 4  # breakpoint precedes the RET
    elif count:
        application = cycles - start - fake
        # 25% + 2048 cycles reserves Timer2 and full-duplex UART interrupts.
        # Measured Timer2 ISR=716 cycles. At 38400 baud, 2*3840 UART ISRs/s,
        # each <=100 cycles: <19% CPU. This is a running-loop estimate, not
        # exhaustive WCET; failures/timeouts and input-driven branches remain.
        estimate = ((application + bound) * 5 + 3) // 4 + 2048
        rows.append((estimate, application, bound, *values[:2]))
assert rows and "profile_done" in text, "Incomplete simulator run"
worst = max(rows)
summary = ["cycles,production_cpu,mcal_bound,phase,pass"]
summary += [",".join(map(str, row)) for row in rows]
(root / "passes.csv").write_text("\n".join(summary) + "\n")
print(f"AVR running-loop estimate: {worst[0]} cycles / {worst[0]/8000:.3f} ms "
      f"(phase {worst[3]}, pass {worst[4]}); 64000-cycle budget EXCEEDED")
print(f"Components: production={worst[1]}, MCAL bound={worst[2]}, "
      "interrupt reserve=25% + 2048 cycles")
commit = (root / "commit.log").read_text()
ticks = list(map(int, re.findall(r"# cycles\s+(\d+)", commit)))
assert len(ticks) == 2, "Incomplete pure commit measurement"
assert "RES_OK" in commit, "Pure commit did not start"
print(f"set_commit_with_cal alone: {ticks[1]-ticks[0]} cycles / "
      f"{(ticks[1]-ticks[0])/8000:.4f} ms")
wrap = (root / "wrap.log").read_text()
ticks = list(map(int, re.findall(r"# cycles\s+(\d+)", wrap)))
assert len(ticks) == 2, "Incomplete epoch-wrap measurement"
assert "RES_OK" in wrap, "Epoch-wrap commit did not start"
print(f"Epoch-wrap commit alone: {ticks[1]-ticks[0]} cycles / "
      f"{(ticks[1]-ticks[0])/8000:.4f} ms")
mcal = (root / "mcal.log").read_text()
calibration = {}
for kind, _, begin, end in re.findall(
        r"BEGIN (\d+) (\d+)\n.*?# cycles\s+(\d+)\n.*?END\n.*?# cycles\s+(\d+)",
        mcal, re.S):
    calibration.setdefault(int(kind), []).append(int(end)-int(begin))
assert len(calibration[9]) == 256 and calibration[32], "Incomplete MCAL calibration"
print(f"Real soft SPI: {max(calibration[9])} cycles/byte; "
      f"30-byte CJ transaction={30*max(calibration[9])} cycles; "
      f"Timer2 ISR={max(calibration[32])} cycles")
