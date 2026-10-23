# Instruction cycles from the installed GNU AVR simulator, compiled at -Os.
param([string]$Gdb='C:/Users/malgh/.platformio/packages/toolchain-atmelavr/bin/avr-gdb.exe')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$out=Join-Path $root 'build/profile'
New-Item -ItemType Directory -Force $out | Out-Null
$bin='C:/Program Files (x86)/Labcenter Electronics/Proteus 8 Professional/Tools/ARDUINO/hardware/tools/avr/bin'
# Keep unchanged register fakes small enough for AVR SRAM. Only the MCAL seam
# differs: aliased fixture A/B slots, FF elsewhere, nonblocking byte writes.
$header=(Get-Content "$root/test/fakes/fake_hw.h" -Raw).Replace('[4096]','[1024]').Replace('[16384]','[128]')
[IO.File]::WriteAllText("$out/fake_hw.h",$header)
$fake=(Get-Content "$root/test/fakes/fake_mcal.c" -Raw).Replace('[4096]','[1024]').Replace('[16384]','[128]')
$fake=$fake.Replace('static uint8_t ports','extern volatile uint32_t profile_delay; extern uint8_t profile_eeprom_read(uint16_t); extern void profile_eeprom_write(uint16_t,uint8_t);'+"`n"+'static uint8_t ports')
$fake=$fake.Replace('us+=delay;','us+=delay; profile_delay+=delay;')
$fake=$fake.Replace('return a<4096?fake_eeprom[a]:0xFF;','return profile_eeprom_read(a);')
$fake=$fake.Replace('fake_eeprom[a]=v;','profile_eeprom_write(a,v);')
$fake=$fake.Replace('if(uart_len>=sizeof fake_uart_log-1) return false;','if(uart_len>=sizeof fake_uart_log-1) uart_len=0;')
$fake="#include `"app/timing.h`"`n"+$fake.Replace('remaining=d<=1000?d:0','remaining=d<=APP_RUN_WINDOW_MS?d:0')
$fake=$fake.Replace('static bool pump;','static bool pump,expired;')
$fake=$fake.Replace('remaining=0; pump=false; }','remaining=0; pump=false; expired=false; }')
$fake=$fake.Replace('if(remaining && --remaining==0) timer_run_stop();','if(remaining && --remaining==0) { expired=true; timer_run_stop(); }')
$fake += @'
#include "app/timing.h"
bool timer_run_expired(void) { return expired; }
void timer_run_ack_expiry(void) { if(!remaining && !pump) expired=false; }
bool timer_run_start_at(uint16_t d,uint32_t at) {
    uint32_t age=tick_ms()-at;
    if(d && d<=APP_RUN_WINDOW_MS && age>=d) expired=true;
    if(expired || !d || d>APP_RUN_WINDOW_MS || age>=d) { timer_run_stop(); return false; }
    timer_run_start((uint16_t)(d-age)); return true;
}
'@
[IO.File]::WriteAllText("$out/fake_mcal.c",$fake)
$sources=Get-Content "$root/sources/hardware_avr.txt" | Where-Object { $_ -and $_ -notmatch '^src/mcal/' } | ForEach-Object { "$root/$_" }
$sources+=@("$root/test/fakes/fake_ad7124.c","$root/test/fakes/fake_tmp126.c","$PSScriptRoot/avr_profile.c")
# No LTO through the register-model seam: application optimisation must not
# infer fake-only constant returns/side effects. Production MCAL is opaque too.
& "$bin/avr-gcc.exe" '-std=c11' '-g' '-Os' '-fshort-enums' '-Wall' '-Wextra' '-Werror' '-mmcu=atmega1284p' '-DF_CPU=8000000UL' '-DFAMILY_TEST' '-DFAMILY_REGISTER_MODEL' "-I$out" "-I$root/include" '-c' "$PSScriptRoot/avr_mcal_wrap.c" '-o' "$out/mcal_wrap.o"
if($LASTEXITCODE) { throw 'MCAL seam compilation failed' }
& "$bin/avr-gcc.exe" '-std=c11' '-g' '-Os' '-fshort-enums' '-Wall' '-Wextra' '-Werror' '-mmcu=atmega1284p' '-DF_CPU=8000000UL' '-DFAMILY_TEST' '-DFAMILY_REGISTER_MODEL' "-I$out" "-I$root/include" '-ffunction-sections' '-fdata-sections' '-Wl,--gc-sections' @sources "$out/mcal_wrap.o" '-o' "$out/profile.elf"
if($LASTEXITCODE) { throw 'AVR profile compilation failed' }
& "$bin/avr-size.exe" '-C' '--mcu=atmega1284p' "$out/profile.elf"
& "$bin/avr-objdump.exe" '-d' "$out/profile.elf" | Out-File "$out/disassembly.txt" -Encoding ascii
# This simulator misclassifies ELF avr:51 as a three-byte-PC AVR. avr:5 has
# the same instruction timings and correct two-byte PC for ATmega1284P. Only
# the simulator ELF architecture flag changes; no instruction bytes change.
$elf=[IO.File]::ReadAllBytes("$out/profile.elf")
if(($elf[36] -band 127) -ne 51) { throw 'Unexpected AVR ELF architecture' }
$elf[36]=($elf[36] -band 128) -bor 5
[IO.File]::WriteAllBytes("$out/profile.elf",$elf)
& "$bin/avr-objcopy.exe" '-O' 'binary' '-j' '.data' "$out/profile.elf" "$out/data.bin"
$commands=@'
target sim
load
break main
run
restore DATA_FILE binary 0x800100
delete 1
break profile_begin
commands
silent
printf "BEGIN %u %u\n", profile_phase, profile_pass
info target
enable IO_BREAKS
continue
end
break profile_end
commands
silent
printf "END %u %u %lu %lu %lu %u\n", profile_phase, profile_pass, fake_spi_bytes, fake_soft_bytes, profile_delay, $io_depth
info target
disable IO_BREAKS
continue
end
break profile_done
'@
$commands=$commands.Replace('DATA_FILE',("$out/data.bin" -replace '\\','/'))
$names=@('gpio_init','gpio_write','gpio_read','gpio_mask','delay_us','spi_init','spi_enable','spi_xfer','spi_soft_xfer','timer_init','tick_ms','timer_run_start','timer_run_start_at','timer_run_stop','timer_run_remaining','timer_run_active','timer_run_expired','timer_run_ack_expiry','timer_run_static_high','wdt_feed','reset_cause','fuses_read','fuses_ok','flow_check','ee_read','ee_ready','ee_write_byte','uart_init','uart_put','uart_get','uart_tx_complete')
$symbols=& "$bin/avr-nm.exe" '-S' '--defined-only' "$out/profile.elf"
$returns=@()
foreach($line in Get-Content "$out/disassembly.txt") {
    if($line -match '^\s*([0-9a-f]+):.*\bret\s*$') { $returns += [Convert]::ToInt32($Matches[1],16) }
}
$ioCommands=''; $breakNo=5
for($n=0;$n -lt $names.Length;$n++) {
    $symbol=$symbols | Where-Object { $_ -match ('\s'+$names[$n]+'$') }
    if(-not $symbol) { continue }
    $words=$symbol.Trim() -split '\s+'
    $address=[Convert]::ToInt32($words[0],16); $size=[Convert]::ToInt32($words[1],16)
    $ioCommands+="break *((void(*)(void))$address)`ncommands`nsilent`nif `$io_depth==0`nprintf `"IO_BEGIN $($n+1) %u\n`", (unsigned int)`$r24+256*(unsigned int)`$r25`ninfo target`nend`nset `$io_depth=`$io_depth+1`ncontinue`nend`n"
    $breakNo++
    $functionReturns=@($returns | Where-Object { $_ -ge $address -and $_ -lt $address+$size })
    if(-not $functionReturns.Length) { throw "Wrapper $($names[$n]) has no RET" }
    foreach($ret in $functionReturns) {
        $ioCommands+="break *((void(*)(void))$ret)`ncommands`nsilent`nset `$io_depth=`$io_depth-1`nif `$io_depth==0`nprintf `"IO_END\n`"`ninfo target`nend`ncontinue`nend`n"
        $breakNo++
    }
}
$commands=$commands.Replace('IO_BREAKS',"5-$($breakNo-1)")
$commands+="`n$ioCommands`nset `$io_depth=0`ndisable 5-$($breakNo-1)`ncontinue`nprintf `"PROFILE_ERRORS %u MIXED %u\n`",profile_errors,profile_mixed`nquit`n"
[IO.File]::WriteAllText("$out/profile.gdb",$commands)
python "$PSScriptRoot/run_gdb.py" $Gdb "$out/profile.gdb" "$out/profile.elf" "$out/cycles.log"
if($LASTEXITCODE) { throw 'AVR simulator failed; inspect cycles.log' }
# Calibrate the actual GPIO/software-SPI/timer implementations, without fakes.
& "$bin/avr-gcc.exe" '-std=c11' '-g' '-Os' '-fshort-enums' '-Wall' '-Wextra' '-Werror' '-mmcu=atmega1284p' '-DF_CPU=8000000UL' "-I$root/include" "$root/src/mcal/gpio.c" "$root/src/mcal/timer.c" "$root/src/mcal/spi.c" "$root/src/drivers/keys.c" "$root/src/board/board_cfg_24.c" "$PSScriptRoot/avr_mcal_cycles.c" "$PSScriptRoot/avr_store_cycles.c" "$root/src/services/settings.c" "$root/src/services/settings_cal.c" "$root/src/services/settings_store.c" '-o' "$out/mcal.elf"
if($LASTEXITCODE) { throw 'MCAL calibration compilation failed' }
& "$bin/avr-objcopy.exe" '-O' 'binary' '-j' '.data' "$out/mcal.elf" "$out/mcal_data.bin"
$elf=[IO.File]::ReadAllBytes("$out/mcal.elf"); $elf[36]=($elf[36] -band 128) -bor 5
[IO.File]::WriteAllBytes("$out/mcal.elf",$elf)
$mcal=@'
target sim
load
break main
run
restore DATA_FILE binary 0x800100
delete 1
break cycle_begin
commands
silent
printf "BEGIN %u %u\n",cycle_kind,cycle_value
info target
continue
end
break cycle_end
commands
silent
printf "END\n"
info target
continue
end
break cycle_done
continue
printf "MCAL_ERRORS %u\n",cycle_errors
quit
'@
$mcal=$mcal.Replace('DATA_FILE',("$out/mcal_data.bin" -replace '\\','/'))
[IO.File]::WriteAllText("$out/mcal.gdb",$mcal)
python "$PSScriptRoot/run_gdb.py" $Gdb "$out/mcal.gdb" "$out/mcal.elf" "$out/mcal.log"
if($LASTEXITCODE) { throw 'MCAL calibration simulation failed' }
python "$PSScriptRoot/profile_summary.py" $out | Tee-Object -FilePath "$out/summary.txt"
if($LASTEXITCODE) { throw 'Cycle report failed' }
