"""Instruction counts, excluding opaque register-model CPU, plus MCAL bounds."""
from pathlib import Path
import re
import subprocess
import sys

root=Path(sys.argv[1])
header=(Path(__file__).resolve().parents[2]/"include/app/timing.h").read_text()
def limit(name):
    return int(re.search(r"#define\s+"+name+r"\s+(\d+)",header)[1])
cycle_budget=limit("APP_LOOP_BUDGET_MS")*limit("APP_AVR_CYCLES_PER_MS")
text=(root/"cycles.log").read_text()
mcal=(root/"mcal.log").read_text()
from profile_costs import calibration_from,bounds,call_cost
calibration=calibration_from(mcal)
assert "MCAL_ERRORS 0" in mcal, "Target MCAL/image checks failed"
assert len(calibration[9])==256 and len(calibration[32])==2049
soft=max(c for _,c in calibration[9]); interrupt=max(c for _,c in calibration[32])
assert soft<=512 and interrupt<=250, "MCAL cycle budget exceeded"
assert len(calibration[33])==3 and calibration[34]
prep=max(c for _,c in calibration[34]); begin=max(c for _,c in calibration[33])
assert prep<=8000 and begin<=8000, "Unbounded commit preparation"
assert "PROFILE_ERRORS 0 MIXED 63 REARM 63" in text, "Combined-load/newest-result evidence missing/failed"
retry=tuple(map(int,re.search(r"REF_RETRY FLAGS (\d+) RECOVERY (\d+)",text).groups()))
assert retry[0]==31 and 0<retry[1]<3000, "Transient/held-high REF recovery regression failed"

assert len(calibration[2])==68 and len(calibration[3])==68
assert max(c for _,c in calibration[2])<=60 and max(c for _,c in calibration[3])<=60,"GPIO cycle budget exceeded"
costs=bounds(calibration)
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
        bound+=call_cost(costs,io,arg)
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
assert {0,1,2,3,4,5,6,8,9,11,12,13,14,15,16,17,18,19,20,21,22}<={r[3] for r in rows}
worst=max(rows); mixed=max(r for r in rows if r[3]==9)
(root/"passes.csv").write_text("cycles,production_cpu,mcal_bound,phase,pass\n"+
    "\n".join(",".join(map(str,r)) for r in rows)+"\n")
print(f"AVR loop: {len(rows)} measured passes; worst={worst[0]} cycles / {worst[0]/8000:.3f} ms "
      f"(phase {worst[3]}, pass {worst[4]})")
print(f"Components: production={worst[1]}, MCAL bound={worst[2]}, reserve=25% + 2048 cycles")
print(f"Combined UI/Modbus flood/commit/CJ/slot/ACK: {mixed[0]} cycles; evidence flags=63; functional errors=0")
print("Newest hot/C01 result: AVR key ACK refused; validated completion keeps PWM off; evidence flags=63")
print(f"REF retry: first scan after successful test validates in {retry[1]} ms after wire restoration; fresh ACK restores RUN; held-high never validates; flags=31")
print(f"GPIO bounds: write={costs[2]}, read={costs[3]}, 1-us delay={costs[5]} cycles (all 32 pins + invalid guards)")
print(f"Soft SPI: {soft} cycles/byte; Timer2 ISR: {interrupt} cycles (2049 samples)")
print(f"Commit begin max: {begin} cycles; preparation step max: {prep} cycles "
      f"({len(calibration[34])} samples); target image checks=0 errors")
assert worst[0]<=cycle_budget, f"{cycle_budget}-cycle loop budget EXCEEDED: {worst[0]}"
print(f"AVR timing gate: PASS (<={cycle_budget} cycles including reserve)")

print(f"UI: {tasks.get(1)} cycles; Modbus: {tasks.get(2)} cycles; view hooks: {tasks.get(3)} cycles (includes Timer2 + two RX interrupts)")
print(f"UART RX ISR: {rx_isr} cycles; pop: {max(c for _,c in calibration[37])}; clock: {max(c for _,c in calibration[38])}")
assert tasks.keys()>={1,2,3} and max(tasks[1],tasks[2])<=8000, "UI/Modbus 1ms task budget EXCEEDED"

clocks=list(map(int,re.findall(r"^CLOCK (\d+)$",text,re.M)))
assert clocks==[(r[0]+7)//8 for r in rows], "Every pass must advance by its measured cycle estimate"
stack,capacity=map(int,re.search(r"STACK (\d+) CAPACITY (\d+)",text).groups())
stack_header=(Path(__file__).resolve().parents[2]/"include/app/stack_budget.h").read_text()
allowance=int(re.search(r"#define APP_STACK_BYTES (\d+)",stack_header)[1])
assert 0<stack<allowance and stack+32<capacity, "Stack allowance/paint capacity exceeded"
from irq_stack import measure
compiler_bin=sys.argv[2] if len(sys.argv)>2 else "C:/Program Files (x86)/Labcenter Electronics/Proteus 8 Professional/Tools/ARDUINO/hardware/tools/avr/bin"
gdb=sys.argv[3] if len(sys.argv)>3 else Path.home()/".platformio/packages/toolchain-atmelavr/bin/avr-gdb.exe"
# Every GPIO bit update must remain atomic against Timer2's PB3 stop.
disassembly=subprocess.check_output([str(Path(compiler_bin)/"avr-objdump.exe"),"-d",str(root/"mcal.elf")],text=True)
body=re.search(r"<gpio_write>:\n(.*?)(?=\n[0-9a-f]+ <)",disassembly,re.S)[1]
bit_ops={(op,int(port,16),int(bit)) for op,port,bit in re.findall(r"\b(sbi|cbi)\s+0x([0-9a-f]+),\s*(\d+)",body)}
assert all((op,port,bit) in bit_ops for op in ("sbi","cbi") for port in (2,5,8,11) for bit in range(8)),"GPIO update is not atomic"
irq_overlay=measure(root.resolve(),compiler_bin,gdb)
assert stack+irq_overlay<allowance,"Stack including worst ISR overlay EXCEEDED"
scans=tuple(map(int,re.search(r"SCANS (\d+) (\d+) (\d+) COUNTS (\d+) (\d+) (\d+)",text).groups()))
assert scans[3:]==(3,3,3) and max(scans[:3])<limit("APP_SCAN_DEADLINE_MS"), "Sustained scan cadence gate failed"
assert max(scans[:3])<=1100, "Fixed-cadence completion gap exceeded 1100 ms"
print(f"Measured-clock completion gaps (5/10/20 ms minimum cadence): {scans[0]}/{scans[1]}/{scans[2]} ms; 3/3 validated each")
jitter=[tuple(map(int,m)) for m in re.findall(r"^JITTER (\d+) (\d+) COUNT (\d+) REF (\d+)$",text,re.M)]
assert len(jitter)==4 and [r[0] for r in jitter]==list(range(4)), "Jitter evidence missing"
assert all(0<gap<=1100 and count==8 and ref>0 for _,gap,count,ref in jitter), "Healthy REF/jitter completion gap exceeded 1100 ms"
for pattern,gap,count,ref in jitter:
    print(f"Measured-clock jitter {pattern}: worst completion gap={gap} ms; {count}/8 validated, REF exercised, RUN uninterrupted")
print(f"Integrated stack high-water: {stack} bytes; separately painted ISR overlay={irq_overlay}; conservative gate={stack+irq_overlay}/{allowance} bytes")
print(f"Painted simulator capacity={capacity}; real Timer2 + UART RX preemption; ISR overlay covers interruption inside pure/library calls")
