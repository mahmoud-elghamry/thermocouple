"""Keep simulator evidence, discarding repetitive section inventories."""
from pathlib import Path
import subprocess
import sys
import time

exe,commands,elf,log=sys.argv[1:]
start=time.monotonic()
with Path(log).open("w") as out:
    proc=subprocess.Popen([exe,"-batch","-x",commands,elf],stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,text=True,errors="replace")
    for line in proc.stdout:
        if time.monotonic()-start>480:
            proc.kill(); raise SystemExit("AVR simulator exceeded 480 seconds")
        s=line.strip()
        if s.startswith(("BEGIN ","END","IO_","# cycles","MCAL_ERRORS","PROFILE_ERRORS")) or \
           any(x in s for x in ("profile_done","cycle_done","Error","error","No symbol","No registers")):
            out.write(s+"\n")
    result=proc.wait()
print(f"AVR simulator: {time.monotonic()-start:.1f} s")
raise SystemExit(result)
