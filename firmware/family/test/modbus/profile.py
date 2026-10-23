"""AVR simulator cycle gate; all artifacts stay in this lane's output folder."""
from pathlib import Path
import re
import subprocess
import sys

out = Path(__file__).resolve().parent / "output"
root = Path(__file__).resolve().parents[2]
bin_dir = Path(sys.argv[1]).parent
elf = out / "profile.elf"
sources = sorted((root / "src/app").glob("modbus*.c")) + [Path(__file__).with_name("avr_profile.c")]
subprocess.run([str(bin_dir / "avr-gcc.exe"), "-std=c11", "-g", "-Os", "-mmcu=atmega1284p",
                "-Wall", "-Wextra", "-Werror", "-I" + str(root / "include"),
                *map(str, sources), "-o", str(elf)], check=True)
subprocess.run([str(bin_dir / "avr-objcopy.exe"), "-O", "binary", "-j", ".data", str(elf), str(out / "data.bin")], check=True)
data = bytearray(elf.read_bytes())
assert data[36] & 127 == 51
data[36] = (data[36] & 128) | 5  # ATmega1284P has a two-byte program counter.
elf.write_bytes(data)
commands = f"""target sim
load
break main
run
restore {(out / 'data.bin').as_posix()} binary 0x800100
delete 1
break profile_begin
commands
silent
printf "BEGIN %u %u\\n", profile_case, profile_pass
info target
continue
end
break profile_end
commands
silent
printf "END\\n"
info target
continue
end
break profile_done
continue
printf "ERRORS %u\\n", profile_errors
quit
"""
if not (out / "data.bin").stat().st_size:
    commands = "\n".join(x for x in commands.splitlines() if not x.startswith("restore "))
(out / "profile.gdb").write_text(commands)
run = subprocess.run([str(bin_dir / "avr-gdb.exe"), "-batch", "-x", str(out / "profile.gdb"), str(elf)],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, text=True, errors="replace")
(out / "simulator.log").write_text(run.stdout)
log = "\n".join(x.strip() for x in run.stdout.splitlines()
                if x.strip().startswith(("BEGIN", "END", "# cycles", "ERRORS")) or "profile_done" in x)
(out / "cycles.log").write_text(log)
assert run.returncode == 0 and "ERRORS 0" in log and "profile_done" in log, log[-2000:]
rows = [(int(end) - int(start), int(case), int(step)) for case, step, start, end in re.findall(
    r"BEGIN (\d+) (\d+)\n# cycles\s+(\d+)\nEND\n# cycles\s+(\d+)", log)]
assert rows
worst = max(rows)
summary = (f"AVR Modbus: {len(rows)} steps; worst {worst[0]} cycles / {worst[0]/8000:.3f} ms "
           f"(request {worst[1]}, step {worst[2]}); +2000 driver/ISR reserve = {(worst[0]+2000)/8000:.3f} ms")
(out / "timing.txt").write_text(summary + "\n")
print(summary)
assert worst[0] + 2000 <= 8000, "1 ms budget exceeded (8MHz AVR, including driver/ISR reserve)"
