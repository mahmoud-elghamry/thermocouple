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
    $exe=Join-Path $out 'test_hardware.exe'
    $installer=Split-Path $vswhere
    $cmd="set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /fsanitize=address /Zi /DFAMILY_TEST /D_CRT_SECURE_NO_WARNINGS /I`"$root/include`" /I`"$root/test/fakes`" $quoted /Fe:`"$exe`" /Fo:`"$out/`" /Fd:`"$out/hardware.pdb`""
    Run $env:ComSpec @('/d','/s','/c',$cmd)
    Run $env:ComSpec @('/d','/s','/c',"set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && `"$exe`"")
}
if(-not $HostOnly) {
    $bin='C:/Program Files (x86)/Labcenter Electronics/Proteus 8 Professional/Tools/ARDUINO/hardware/tools/avr/bin'
    $gcc=Join-Path $bin 'avr-gcc.exe'
    $elf=Join-Path $out 'thermo24_f0.elf'
    $flags=@('-std=c11','-Os','-Wall','-Wextra','-Werror','-mmcu=atmega1284p','-DF_CPU=8000000UL',"-I$root/include",'-ffunction-sections','-fdata-sections','-Wl,--gc-sections,--section-start=.image_crc=0x1FFFE,--undefined=image_crc')
    Run $gcc ($flags+@(Sources 'hardware_avr')+@('-o',$elf))
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
    if($ram+1024 -gt 12288) { throw "RAM budget exceeded: $ram + 1024 stack" }
    if($end+2 -gt 65536) { throw "Flash budget exceeded: $end + 2 CRC" }
    Write-Host "RAM with 1024-byte stack allowance: $($ram+1024)/12288; flash CRC storage: 2 bytes"
    Run (Join-Path $bin 'avr-objcopy.exe') @('-O','ihex','-R','.eeprom',$elf,(Join-Path $out 'thermo24_f0.hex'))
    Run (Join-Path $bin 'avr-size.exe') @('-C','--mcu=atmega1284p',$elf)
}
Stop-Transcript | Out-Null
