"""Independent painted ISR overlay, added to the integrated stack high-water."""
from pathlib import Path
import re
import subprocess

def measure(out,compiler_bin,gdb):
    source=Path(__file__).resolve().parent
    root=source.parents[1]
    elf=out/"irq_stack.elf"
    def tool(name,*args):
        subprocess.run([str(Path(compiler_bin)/(name+".exe")),*map(str,args)],check=True,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    tool("avr-gcc","-std=c11","-g","-Os","-mcall-prologues","-fshort-enums",
         "-Wall","-Wextra","-Werror","-mmcu=atmega1284p","-DF_CPU=8000000UL",
         "-DFAMILY_REGISTER_MODEL","-I"+str(root/"include"),"-ffunction-sections",
         "-fdata-sections","-Wl,--relax,--gc-sections",source/"avr_irq_stack.c",
         source/"avr_profile_irq.c","-o",elf)
    tool("avr-objcopy","-O","binary","-j",".data",elf,out/"irq_stack_data.bin")
    data=bytearray(elf.read_bytes());assert data[36]&127==51
    data[36]=(data[36]&128)|5;elf.write_bytes(data)
    restore=f"{restore}" if (out/"irq_stack_data.bin").stat().st_size else ""
    script=out/"irq_stack.gdb"
    script.write_text(f"""target sim
load
break main
run
{restore}
delete 1
break irq_stack_done
continue
printf "IRQ_STACK %u ERRORS %u\\n",irq_stack_bytes,irq_stack_errors
quit
""")
    run=subprocess.run([str(gdb),"-batch","-x",str(script),str(elf)],check=True,
                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
    (out/"irq_stack.log").write_text(run.stdout)
    match=re.search(r"IRQ_STACK (\d+) ERRORS (\d+)",run.stdout)
    assert match and int(match[2])==0,"ISR overlay probe failed"
    size=int(match[1]);assert 18<=size<64,"ISR overlay probe outside painted capacity"
    return size
