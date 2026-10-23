"""Production ELF gate: S0 must precede stack painting, independent of link order."""
import subprocess
import sys


def check(nm, elf):
    symbols = {}
    for line in subprocess.check_output([nm, '-n', elf], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    early, paint = (symbols[name] for name in ('early_init', 'app_stack_paint'))
    if early >= paint:
        raise ValueError(f'S0 early_init 0x{early:x} must precede stack paint 0x{paint:x}')
    for name in ('__do_copy_data', '__do_clear_bss'):
        if name in symbols and not early < symbols[name] < paint:
            raise ValueError(f'{name} must lie between S0 and .init5 stack paint')
    if paint >= symbols['main']:
        raise ValueError('Stack paint must run before main')
    print(f'Startup order: PASS (early_init=0x{early:x}, app_stack_paint=0x{paint:x})')


if __name__ == '__main__':
    try:
        check(*sys.argv[1:])
    except (KeyError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f'Startup order: FAIL ({error})')
