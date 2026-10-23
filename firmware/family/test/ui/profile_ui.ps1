$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$out=Join-Path $PSScriptRoot 'output'
New-Item -ItemType Directory -Force $out | Out-Null
$bin='C:/Program Files (x86)/Labcenter Electronics/Proteus 8 Professional/Tools/ARDUINO/hardware/tools/avr/bin'
$src=@('src/app/ui.c','src/app/ui_edit.c','src/app/ui_screens.c','src/app/ui_format.c',
 'src/services/settings.c','src/services/fault.c','test/ui/fake_ui.c','test/ui/profile_ui.c') | ForEach-Object { Join-Path $root $_ }
$elf=Join-Path $out 'profile.elf'
& "$bin/avr-gcc.exe" '-std=c11' '-g' '-Os' '-fshort-enums' '-Wall' '-Wextra' '-Werror' '-mmcu=atmega1284p' '-DF_CPU=8000000UL' '-DUI_PROFILE' "-I$root/include" @src '-o' $elf
if($LASTEXITCODE) { throw 'UI profile compilation failed' }
& "$bin/avr-objcopy.exe" '-O' 'binary' '-j' '.data' $elf "$out/profile-data.bin"
# Same installed simulator correction as test/integration/profile_avr.ps1.
$bytes=[IO.File]::ReadAllBytes($elf); $bytes[36]=($bytes[36] -band 128) -bor 5
[IO.File]::WriteAllBytes($elf,$bytes)
$gdb=@'
target sim
load
break main
run
restore DATA_FILE binary 0x800100
delete 1
break ui_profile_begin
commands
silent
printf "BEGIN %u\n",profile_case
info target
continue
end
break ui_profile_end
commands
silent
printf "END\n"
info target
continue
end
break ui_profile_done
continue
quit
'@
$gdb=$gdb.Replace('DATA_FILE',("$out/profile-data.bin" -replace '\\','/'))
[IO.File]::WriteAllText("$out/profile.gdb",$gdb)
& python "$PSScriptRoot/profile_summary.py" "$env:USERPROFILE/.platformio/packages/toolchain-atmelavr/bin/avr-gdb.exe" "$out/profile.gdb" $elf "$out/profile-cycles.txt"
if($LASTEXITCODE) { throw 'UI profile budget failed; inspect profile-cycles.txt' }
