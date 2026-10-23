"""Instruction counts, excluding opaque register-model CPU, plus MCAL bounds."""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1])
header=(Path(__file__).resolve().parents[2]/"include/app/timing.h").read_text()
def limit(name):
    return int(re.search(r"#define\s+"+name+r"\s+(\d+)",header)[1])
cycle_budget=limit("APP_LOOP_BUDGET_MS")*limit("APP_AVR_CYCLES_PER_MS")
text=(root/"cycles.log").read_text()
mcal=(root/"mcal.log").read_text()
calibration={}
for kind, value, begin, end in re.findall(
        r"BEGIN (\d+) (\d+)\n.*?# cycles\s+(\d+)\n.*?END\n.*?# cycles\s+(\d+)",mcal,re.S):
    calibration.setdefault(int(kind),[]).append((int(value),int(end)-int(begin)))
assert "MCAL_ERRORS 0" in mcal, "Target MCAL/image checks failed"
assert len(calibration[9])==256 and len(calibration[32])==2049
soft=max(c for _,c in calibration[9]); interrupt=max(c for _,c in calibration[32])
assert soft<=512 and interrupt<=250, "MCAL cycle budget exceeded"
assert len(calibration[33])==3 and calibration[34]
prep=max(c for _,c in calibration[34]); begin=max(c for _,c in calibration[33])
assert prep<=8000 and begin<=8000, "Unbounded commit preparation"
assert "PROFILE_ERRORS 0 MIXED 63 REARM 63" in text, "Combined-load/newest-result evidence missing/failed"

# Conservative actual MCAL costs, including call/return and branch margin.
# Soft SPI uses all-256-TX calibration; delay allows twice the requested time.
costs={1:400,2:100,3:100,4:60,6:30,7:30,8:110,9:soft+16,
       10:100,11:40,12:300,13:300,14:100,15:40,16:60,17:20,18:80,
       19:100,20:10,21:20,22:100,23:150,24:150,25:80,26:20,
       27:100,28:100,29:100,30:80,31:60}
costs.update({32:max(c for _,c in calibration[38])+40,33:400,
              34:max(c for _,c in calibration[37])+32,35:max(c for _,c in calibration[39])+32,36:40})
rx_isr=max(c for _,c in calibration[36]); tasks={}; task=None
marker=None; rows=[]; start=fake=bound=count=0; io_start=None; calls={}
for line in text.splitlines():
    match=re.fullmatch(r"(BEGIN|END|IO_BEGIN|IO_END|TASK_BEGIN|TASK_END)(?: (.*))?",line)
    if match: marker=match[1],list(map(int,(match[2] or "").split()))
    match=re.match(r"# cycles\s+(\d+)",line.strip())
    if not match or not marker: continue
    kind,values=marker; marker=None; cycles=int(match[1])
    if kind=="TASK_BEGIN":
        assert task is None
        task=(values[0],cycles,fake,bound)
    elif kind=="TASK_END":
        assert task is not None
        which,task_begin,old_fake,old_bound=task
        total=cycles-task_begin-(fake-old_fake)+(bound-old_bound)+interrupt+2*rx_isr
        tasks[which]=max(tasks.get(which,0),total); task=None
    elif kind=="BEGIN":
        assert io_start is None
        start=cycles; fake=bound=count=0; calls={}
    elif kind=="IO_BEGIN":
        assert io_start is None, "Overlapping opaque MCAL calls"
        io_start=cycles; io,arg=values
        bound+=16*arg+40 if io==5 else costs[io]
        count+=1; calls[io]=calls.get(io,0)+1
    elif kind=="IO_END":
        assert io_start is not None
        fake+=cycles-io_start+4  # breakpoint immediately precedes RET
        io_start=None
    else:
        assert io_start is None and len(values)==6 and values[5]==0, "Unbalanced MCAL exits"
        assert calls.get(8,0)==values[2] and calls.get(9,0)==values[3], "SPI accounting mismatch"
        application=cycles-start-fake
        assert application>=0 and count
        estimate=((application+bound)*5+3)//4+2048
        rows.append((estimate,application,bound,*values[:2]))
assert rows and "profile_done" in text, "Incomplete simulator run"
assert {0,1,2,3,4,5,6,8,9,11,12,13,14}<={r[3] for r in rows}
worst=max(rows); mixed=max(r for r in rows if r[3]==9)
(root/"passes.csv").write_text("cycles,production_cpu,mcal_bound,phase,pass\n"+
    "\n".join(",".join(map(str,r)) for r in rows)+"\n")
print(f"AVR loop: {len(rows)} measured passes; worst={worst[0]} cycles / {worst[0]/8000:.3f} ms "
      f"(phase {worst[3]}, pass {worst[4]})")
print(f"Components: production={worst[1]}, MCAL bound={worst[2]}, reserve=25% + 2048 cycles")
print(f"Combined UI/Modbus flood/commit/CJ/slot/ACK: {mixed[0]} cycles; evidence flags=63; functional errors=0")
print("Newest hot/C01 result: AVR key ACK refused; validated completion keeps PWM off; evidence flags=63")
print(f"Soft SPI: {soft} cycles/byte; Timer2 ISR: {interrupt} cycles (2049 samples)")
print(f"Commit begin max: {begin} cycles; preparation step max: {prep} cycles "
      f"({len(calibration[34])} samples); target image checks=0 errors")
assert worst[0]<=cycle_budget, f"{cycle_budget}-cycle loop budget EXCEEDED: {worst[0]}"
print(f"AVR timing gate: PASS (<={cycle_budget} cycles including reserve)")

print(f"UI: {tasks.get(1)} cycles; Modbus: {tasks.get(2)} cycles; view hooks: {tasks.get(3)} cycles (includes Timer2 + two RX interrupts)")
print(f"UART RX ISR: {rx_isr} cycles; pop: {max(c for _,c in calibration[37])}; clock: {max(c for _,c in calibration[38])}")
assert tasks.keys()>={1,2,3} and max(tasks[1],tasks[2])<=8000, "UI/Modbus 1ms task budget EXCEEDED"
