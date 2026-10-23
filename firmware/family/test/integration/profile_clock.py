"""Feed each measured AVR pass back into the register-model clock.

GDB has no Python support here. Its profile_end breakpoint returns to the
console; this local controller calculates exactly the summary's cycle bound,
writes the elapsed microseconds, and resumes. No target cycles are assumed.
"""
from pathlib import Path
import os
import atexit
import queue
import re
import subprocess
import sys
import threading
import time
from profile_costs import calibration_from,bounds,call_cost

exe,commands,elf,log=sys.argv[1:]
costs=bounds(calibration_from(Path(log).with_name("mcal.log").read_text()))
proc=subprocess.Popen([exe,"-q","-nx","-x",commands,elf],stdin=subprocess.PIPE,
                      stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
atexit.register(lambda: proc.kill() if proc.poll() is None else None)
chunks=queue.Queue()
def reader():
    while True:
        data=os.read(proc.stdout.fileno(),65536)
        chunks.put(data)
        if not data: return
threading.Thread(target=reader,daemon=True).start()
started=time.monotonic(); buffer=""; marker=None; cycle=begin=fake=bound=0
io_start=None; pending=None; passes=0; done=False; finishing=False
with Path(log).open("w") as out:
    def line_received(line):
        global marker,cycle,begin,fake,bound,io_start,pending,done
        line=line.strip()
        if line.startswith(("BEGIN ","END","IO_","TASK_","# cycles","PROFILE_ERRORS","STACK ","CLOCK ","SCANS ","JITTER ","REF_RETRY ")) or \
           any(x in line for x in ("profile_done","Error","error","No symbol","No registers")):
            out.write(line+"\n")
        m=re.fullmatch(r"(BEGIN|END|IO_BEGIN|IO_END)(?: (.*))?",line)
        if m: marker=m[1],list(map(int,(m[2] or "").split()))
        m=re.match(r"# cycles\s+(\d+)",line)
        if m:
            cycle=int(m[1])
            if marker:
                kind,values=marker; marker=None
                if kind=="BEGIN": begin=cycle;fake=bound=0
                elif kind=="IO_BEGIN":
                    assert io_start is None
                    io_start=cycle;io,arg=values
                    bound+=call_cost(costs,io,arg)
                elif kind=="IO_END":
                    assert io_start is not None
                    fake+=cycle-io_start+4;io_start=None
                else:
                    assert io_start is None and values[5]==0
                    estimated=((cycle-begin-fake+bound)*5+3)//4+2048
                    pending=(estimated+7)//8
        if "profile_done" in line: done=True
    while True:
        if time.monotonic()-started>1800:
            proc.kill();raise SystemExit("Clock-coupled AVR profiler exceeded 30 minutes")
        try: data=chunks.get(timeout=30)
        except queue.Empty:
            if proc.poll() is not None: break
            continue
        if not data: break
        buffer+=data.decode(errors="replace")
        while "\n" in buffer or "(gdb) " in buffer:
            eol=buffer.find("\n");prompt=buffer.find("(gdb) ")
            if prompt>=0 and (eol<0 or prompt<eol):
                line_received(buffer[:prompt]);buffer=buffer[prompt+6:]
                if done and not finishing:
                    finishing=True
                    cmd='printf "PROFILE_ERRORS %u MIXED %u REARM %u\\n",profile_errors,profile_mixed,profile_rearm\nprintf "PROFILE_FAILURE %u\\n",profile_failure\nprintf "STACK %u CAPACITY %u\\n",profile_stack,profile_stack_capacity\nprintf "SCANS %u %u %u COUNTS %u %u %u\\n",profile_scan_ms[0],profile_scan_ms[1],profile_scan_ms[2],profile_scan_count[0],profile_scan_count[1],profile_scan_count[2]\nquit\ny\n'
                    jitter=''.join(f'printf "JITTER {p} %u COUNT %u REF %u\\n",profile_gap_ms[{p}],profile_gap_count[{p}],profile_ref_seen[{p}]\n' for p in range(4))
                    cmd=cmd.replace('quit\ny\n',jitter+'quit\ny\n')
                    cmd=cmd.replace('quit\ny\n','printf "REF_RETRY FLAGS %u RECOVERY %u\\n",profile_ref_retry,profile_ref_recovery_ms\nquit\ny\n')
                elif pending is not None:
                    passes+=1
                    out.write(f"CLOCK {pending}\n")
                    cmd=f"set var profile_elapsed_us={pending}\ncontinue\n";pending=None
                else:
                    continue # prompt after the preceding set/printf command
                proc.stdin.write(cmd.encode());proc.stdin.flush()
            else:
                line_received(buffer[:eol]);buffer=buffer[eol+1:]
    result=proc.wait()
print(f"Clock-coupled AVR simulator: {passes} passes, {time.monotonic()-started:.1f} s")
raise SystemExit(result)
