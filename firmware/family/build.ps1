param([switch]$HostOnly,[switch]$AvrOnly)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$out=Join-Path $root 'build'
New-Item -ItemType Directory -Force $out | Out-Null
Start-Transcript -Path (Join-Path $out 'validation.log') -Force | Out-Null
function Run([string]$file,[string[]]$a) {
    & $file @a 2>&1 | ForEach-Object { Write-Host "$_" }
    if($LASTEXITCODE -ne 0) { throw "$file failed ($LASTEXITCODE)" }
}
function Sources([string]$name) {
    Get-Content (Join-Path $root "sources/$name.txt") | ForEach-Object {
        $s=($_ -replace '#.*','').Trim()
        if($s) { Join-Path $root $s }
    }
}
if(-not $AvrOnly) {
    $vswhere='C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe'
    $vs=& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if(-not $vs) { throw 'MSVC build tools missing' }
    $dev=Join-Path $vs 'Common7/Tools/VsDevCmd.bat'
    $src=@(Sources 'hardware_host')
    $quoted=($src | ForEach-Object { '"'+$_+'"' }) -join ' '
    # hardware_host includes the real F1 shell and register-fake integration
    # scenarios; the obsolete F0 "ACK cannot grant RUN" test is superseded.
    $exe=Join-Path $out 'test_hardware.exe'
    $installer=Split-Path $vswhere
    $cmd="set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /O2 /fsanitize=address /Zi /DFAMILY_TEST /D_CRT_SECURE_NO_WARNINGS /I`"$root/include`" /I`"$root/test/fakes`" $quoted /Fe:`"$exe`" /Fo:`"$out/`" /Fd:`"$out/hardware.pdb`""
    Run $env:ComSpec @('/d','/s','/c',$cmd)
    Run $env:ComSpec @('/d','/s','/c',"set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && `"$exe`"")
    $timerExe=Join-Path $out 'test_timer.exe'
    $cmd="set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /O2 /I`"$root/test/stubs`" /I`"$root/include`" `"$root/src/mcal/timer.c`" `"$root/test/integration/test_timer.c`" /Fe:`"$timerExe`" /Fo:`"$out/`""
    Run $env:ComSpec @('/d','/s','/c',$cmd)
    Run $timerExe @()
    $prepExe=Join-Path $out 'test_prepare.exe'
    $cmd="set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /O2 /I`"$root/include`" `"$root/src/services/settings.c`" `"$root/src/services/settings_cal.c`" `"$root/src/services/settings_store.c`" `"$root/test/integration/test_prepare.c`" /Fe:`"$prepExe`" /Fo:`"$out/`""
    Run $env:ComSpec @('/d','/s','/c',$cmd)
    Run $prepExe @()
}
if(-not $HostOnly) {
    $bin='C:/Program Files (x86)/Labcenter Electronics/Proteus 8 Professional/Tools/ARDUINO/hardware/tools/avr/bin'
    $gcc=Join-Path $bin 'avr-gcc.exe'
    $stackHeader=Get-Content (Join-Path $root 'include/app/stack_budget.h') -Raw
    $stackBytes=[int]([regex]::Match($stackHeader,'#define APP_STACK_BYTES (\d+)u').Groups[1].Value)
    if($stackBytes -lt 1024) { throw 'Stack reservation missing/too small' }
    # The existing pure commit owns a settings + calibration working copy.
    # Keep the shell canary below that frame plus caller/interrupt margin.
    $stackObj=Join-Path $out 'settings_stack.o'
    Run $gcc @('-std=c11','-Os','-fshort-enums','-Wall','-Wextra','-Werror','-mmcu=atmega1284p',"-I$root/include",'-fstack-usage','-c',(Join-Path $root 'src/services/settings_store.c'),'-o',$stackObj)
    $frames=Get-Content (Join-Path $out 'settings_stack.su') | ForEach-Object {
        if($_ -match '\t(\d+)\t') { [int]$Matches[1] }
    }
    $maxFrame=($frames | Measure-Object -Maximum).Maximum
    if(-not $maxFrame -or $maxFrame+384 -gt $stackBytes) { throw "Commit stack frame $maxFrame + 384 margin exceeds $stackBytes" }
    Write-Host "AVR commit frame: $maxFrame bytes; caller/interrupt margin: 384; stack reservation: $stackBytes"
    $elf=Join-Path $out 'thermo24_f1.elf'
    $flags=@('-std=c11','-Os','-fshort-enums','-Wall','-Wextra','-Werror','-mmcu=atmega1284p','-DF_CPU=8000000UL',"-I$root/include",'-ffunction-sections','-fdata-sections','-Wl,--gc-sections,--section-start=.image_crc=0x1FFFE,--undefined=image_crc')
    $application=@(); $mcalObjects=@()
    foreach($source in @(Sources 'hardware_avr')) {
        if($source -match '[\\/]src[\\/]mcal[\\/]') {
            $object=Join-Path $out (([IO.Path]::GetFileNameWithoutExtension($source))+'_mcal.o')
            Run $gcc @('-std=c11','-Os','-fshort-enums','-Wall','-Wextra','-Werror','-mmcu=atmega1284p','-DF_CPU=8000000UL',"-I$root/include",'-ffunction-sections','-fdata-sections','-c',$source,'-o',$object)
            $mcalObjects+=$object
        } else { $application+=$source }
    }
    # Whole-application optimisation, with opaque MCAL calls matching the
    # profiler's separately compiled register-model seam.
    Run $gcc ($flags+@('-flto')+$application+$mcalObjects+@('-o',$elf))
    $objcopy=Join-Path $bin 'avr-objcopy.exe'
    $raw=Join-Path $out 'image.bin'
    Run $objcopy @('-O','binary','-j','.text','-j','.data',$elf,$raw)
    $endLine=& (Join-Path $bin 'avr-nm.exe') '--defined-only' $elf | Select-String ' __data_load_end$'
    if(-not $endLine) { throw '__data_load_end missing' }
    $end=[Convert]::ToInt32(($endLine.ToString() -split '\s+')[0],16)
    $image=[IO.File]::ReadAllBytes($raw)
    if($image.Length -ne $end) { throw 'Flash CRC image extent mismatch' }
    [uint32]$crc=65535
    foreach($byte in $image) {
        $crc=$crc -bxor ([uint32]$byte -shl 8)
        for($bit=0;$bit -lt 8;$bit++) {
            if($crc -band 32768) { $crc=($crc -shl 1) -bxor 4129 } else { $crc=$crc -shl 1 }
            $crc=$crc -band 65535
        }
    }
    $crcFile=Join-Path $out 'image_crc.bin'
    [IO.File]::WriteAllBytes($crcFile,[byte[]]@(($crc -band 255),($crc -shr 8)))
    Run $objcopy @('--update-section',".image_crc=$crcFile",$elf)
    $verified=Join-Path $out 'verified_image.bin'
    Run $objcopy @('-O','binary','--gap-fill=0xFF','-j','.text','-j','.data','-j','.image_crc',$elf,$verified)
    $check=[IO.File]::ReadAllBytes($verified)
    if($check.Length -ne 131072 -or $check[131070] -ne ($crc -band 255) -or $check[131071] -ne ($crc -shr 8)) {
        throw 'Stored flash CRC read-back failed'
    }
    for($i=0;$i -lt $end;$i++) { if($check[$i] -ne $image[$i]) { throw 'Flash changed while inserting CRC' } }
    Write-Host ('Stored flash CRC16: {0:X4}, bytes: {1}' -f $crc,$end)
    $sections=& (Join-Path $bin 'avr-size.exe') '-A' $elf
    [int]$ram=0
    foreach($row in $sections) { if($row -match '^\.(data|bss|noinit)\s+(\d+)') { $ram+=[int]$Matches[2] } }
    if($ram+$stackBytes -gt 12288) { throw "RAM budget exceeded: $ram + $stackBytes stack" }
    if($end+2 -gt 65536) { throw "Flash budget exceeded: $end + 2 CRC" }
    Write-Host "RAM with $stackBytes-byte stack allowance: $($ram+$stackBytes)/12288; flash CRC storage: 2 bytes"
    Run (Join-Path $bin 'avr-objcopy.exe') @('-O','ihex','-R','.eeprom',$elf,(Join-Path $out 'thermo24_f1.hex'))
    Run (Join-Path $bin 'avr-size.exe') @('-C','--mcu=atmega1284p',$elf)
}
Stop-Transcript | Out-Null
