param([switch]$HostOnly,[switch]$AvrOnly,[switch]$CompileOnly)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$flashExceeded=$false
$out=Join-Path $root 'build'
New-Item -ItemType Directory -Force $out | Out-Null
Start-Transcript -Path (Join-Path $out 'validation.log') -Force | Out-Null
function Run([string]$file,[string[]]$a) {
    $previous=$ErrorActionPreference; $ErrorActionPreference='Continue'
    try { & $file @a 2>&1 | ForEach-Object { Write-Host "$_" } }
    finally { $ErrorActionPreference=$previous }
    if($LASTEXITCODE -ne 0) { throw "$file failed ($LASTEXITCODE)" }
}
function Sources([string]$name) {
    Get-Content (Join-Path $root "sources/$name.txt") | ForEach-Object {
        $s=($_ -replace '#.*','').Trim()
        if($s) { Join-Path $root $s }
    }
}
$cppcheck='C:/Program Files/Cppcheck/cppcheck.exe'
if(-not (Test-Path -LiteralPath $cppcheck)) { throw 'Cppcheck 2.22 missing' }
# PROGMEM is an address-space annotation; check both host and AVR branches.
Run $cppcheck @('--enable=warning,portability,performance','--std=c11','--error-exitcode=1','--inline-suppr','-DPROGMEM=',"-I$root/include",(Join-Path $root 'src'))
Write-Host 'Cppcheck: PASS (0 findings)'
if(-not $AvrOnly) {
    $vswhere='C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe'
    $vs=& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if(-not $vs) { throw 'MSVC build tools missing' }
    $dev=Join-Path $vs 'Common7/Tools/VsDevCmd.bat'
    $src=@(Sources 'hardware_host')
    $quoted=($src | ForEach-Object { '"'+$_+'"' }) -join ' '
    # Keep cmd.exe below its 8191-character limit as integration sources grow.
    $response=Join-Path $out 'hardware_sources.rsp'
    [IO.File]::WriteAllText($response,$quoted)
    $quoted='@"'+$response+'"'
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
    $uartExe=Join-Path $out 'test_uart.exe'
    $cmd="set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /O2 /I`"$root/test/stubs`" /I`"$root/include`" `"$root/src/mcal/uart.c`" `"$root/test/integration/test_uart.c`" /Fe:`"$uartExe`" /Fo:`"$out/`""
    Run $env:ComSpec @('/d','/s','/c',$cmd)
    Run $uartExe @()
    $crcExe=Join-Path $out 'test_flash_identity.exe'
    $cmd="set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /O2 /D__AVR__ /I`"$root/test/integration/flash_stub`" /I`"$root/include`" `"$root/src/mcal/flash_crc.c`" `"$root/test/integration/test_flash_identity.c`" /Fe:`"$crcExe`" /Fo:`"$out/`""
    Run $env:ComSpec @('/d','/s','/c',$cmd)
    Run $crcExe @()
    Run 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'test/build_ui.ps1'))
    Run 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'test/build_modbus.ps1'))
    Run 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'test/integration/test_program.ps1'))
    Run 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'test/integration/soak.ps1'),'-WrapTest')
    Run 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'test/integration/soak.ps1'),'-Minutes','15')
    Write-Host 'Extended 60-day soak (separate ~10-minute gate): powershell -File test/integration/soak.ps1'
}
if(-not $HostOnly) {
    $bin='C:/Program Files (x86)/Labcenter Electronics/Proteus 8 Professional/Tools/ARDUINO/hardware/tools/avr/bin'
    $gcc=Join-Path $bin 'avr-gcc.exe'
    $commit=(& git --no-optional-locks -C $root rev-parse HEAD).Trim()
    if($LASTEXITCODE -or $commit -notmatch '^[0-9a-f]{40}([0-9a-f]{24})?$') { throw 'Cannot establish build HEAD' }
    $dirtyLines=@(& git --no-optional-locks -C $root status --porcelain)
    if($LASTEXITCODE) { throw 'Cannot establish dirty state' }
    $dirty=if($dirtyLines.Count) { 1 } else { 0 }
    $shortCommit=$commit.Substring(0,12)
    [IO.File]::WriteAllText((Join-Path $out 'identity_generated.h'),"#define FAMILY_BUILD_HASH `"$shortCommit`"`n#define FAMILY_BUILD_DIRTY $dirty`n")
    $identityHeader=Get-Content (Join-Path $root 'include/app/image_identity.h') -Raw
    $identityAddress=[Convert]::ToInt32(([regex]::Match($identityHeader,'#define APP_IDENTITY_ADDRESS (0x[0-9A-Fa-f]+)').Groups[1].Value),16)
    $identityBytes=[int]([regex]::Match($identityHeader,'#define APP_IDENTITY_BYTES (\d+)u').Groups[1].Value)
    $identityOrigin='0x{0:X}' -f $identityAddress
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
    $flags=@('-std=c11','-Os','-mcall-prologues','-fshort-enums','-Wall','-Wextra','-Werror','-mmcu=atmega1284p','-DF_CPU=8000000UL','-DFAMILY_PRODUCTION_IDENTITY',"-I$out","-I$root/include",'-ffunction-sections','-fdata-sections',"-Wl,--relax,--gc-sections,--section-start=.image_crc=0x1FFFE,--undefined=image_crc,--section-start=.image_identity=$identityOrigin,--undefined=app_image_identity")
    # Keep MCAL opaque to application LTO, matching the profiler's I/O seam.
    $targetSources=@(Sources 'hardware_avr'); $mcalObjects=@()
    foreach($src in ($targetSources | Where-Object { $_ -match 'src[\\/]mcal[\\/]' })) {
        $obj=Join-Path $out ((Split-Path $src -Leaf)+'.o'); $mcalObjects+=$obj
        Run $gcc (@('-std=c11','-Os','-mcall-prologues','-fshort-enums','-Wall','-Wextra','-Werror','-mmcu=atmega1284p','-DF_CPU=8000000UL',"-I$root/include",'-ffunction-sections','-fdata-sections','-c',$src,'-o',$obj))
    }
    Run $gcc ($flags+@('-flto')+@($targetSources | Where-Object { $_ -notmatch 'src[\\/]mcal[\\/]' })+$mcalObjects+@('-o',$elf))
    Run 'python' @((Join-Path $root 'test/integration/check_startup.py'),(Join-Path $bin 'avr-nm.exe'),$elf)
    $objcopy=Join-Path $bin 'avr-objcopy.exe'
    $raw=Join-Path $out 'image.bin'
    Run $objcopy @('-O','binary','-j','.text','-j','.data',$elf,$raw)
    $endLine=& (Join-Path $bin 'avr-nm.exe') '--defined-only' $elf | Select-String ' __data_load_end$'
    if(-not $endLine) { throw '__data_load_end missing' }
    $end=[Convert]::ToInt32(($endLine.ToString() -split '\s+')[0],16)
    $image=[IO.File]::ReadAllBytes($raw)
    if($image.Length -ne $end) { throw 'Flash CRC image extent mismatch' }
    $identityFile=Join-Path $out 'identity.bin'
    Run $objcopy @('-O','binary','-j','.image_identity',$elf,$identityFile)
    $identity=[IO.File]::ReadAllBytes($identityFile)
    $identitySymbol=& (Join-Path $bin 'avr-nm.exe') '--defined-only' $elf | Select-String ' app_image_identity$'
    if($identity.Length -ne $identityBytes -or -not $identitySymbol -or
       [Convert]::ToInt32(($identitySymbol.ToString() -split '\s+')[0],16) -ne $identityAddress) {
        throw 'Embedded identity size/address mismatch'
    }
    $covered=$end+$identityBytes
    [uint32]$crc=65535
    foreach($byte in ($image+$identity)) {
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
    Run $objcopy @('-O','binary','--gap-fill=0xFF','-j','.text','-j','.data','-j','.image_identity','-j','.image_crc',$elf,$verified)
    $check=[IO.File]::ReadAllBytes($verified)
    if($check.Length -ne 131072 -or $check[131070] -ne ($crc -band 255) -or $check[131071] -ne ($crc -shr 8)) {
        throw 'Stored flash CRC read-back failed'
    }
    for($i=0;$i -lt $end;$i++) { if($check[$i] -ne $image[$i]) { throw 'Flash changed while inserting CRC' } }
    for($i=0;$i -lt $identityBytes;$i++) { if($check[$identityAddress+$i] -ne $identity[$i]) { throw 'Identity changed while inserting CRC' } }
    Write-Host ('Stored flash CRC16: {0:X4}, bytes: {1} (code/data {2} + identity {3})' -f $crc,$covered,$end,$identityBytes)
    $sections=& (Join-Path $bin 'avr-size.exe') '-A' $elf
    [int]$ram=0
    foreach($row in $sections) { if($row -match '^\.(data|bss|noinit)\s+(\d+)') { $ram+=[int]$Matches[2] } }
    if($ram+$stackBytes -gt 14336) { throw "RAM budget exceeded: $ram + $stackBytes stack" }
    # Finish every functional/timing gate before reporting a size failure.
    # The limit remains fatal; an oversized image is never reported as PASS.
    $flashExceeded=$covered+2 -gt 98304
    if($flashExceeded) { Write-Host "Flash budget FAIL: $covered + 2 CRC > 98304" }
    Write-Host "RAM with $stackBytes-byte stack allowance: $($ram+$stackBytes)/14336; flash CRC storage: 2 bytes"
    Run (Join-Path $bin 'avr-objcopy.exe') @('-O','ihex','-R','.eeprom',$elf,(Join-Path $out 'thermo24_f1.hex'))
    Run 'python' @((Join-Path $root 'image_metadata.py'),(Join-Path $out 'thermo24_f1.hex'),'--write','--bytes',"$covered",'--crc',"$crc")
    Run (Join-Path $bin 'avr-size.exe') @('-C','--mcu=atmega1284p',$elf)
}
if(-not $HostOnly) {
    $profileArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'test/integration/profile_avr.ps1'))
    if($CompileOnly) { $profileArgs+='-CompileOnly' }
    Run 'powershell.exe' $profileArgs
}
Stop-Transcript | Out-Null
if($flashExceeded) { throw "Flash budget exceeded: $covered + 2 CRC > 98304 (10 section 2)" }
