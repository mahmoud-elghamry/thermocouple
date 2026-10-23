# 24-channel ATmega1284P only; 02 sections 6-7. Never substitutes a legacy image.
[CmdletBinding()]
param(
    [string]$Image='build/thermo24_f1.hex', # Intel HEX: CRC-patched by build.ps1, read by any avrdude build
    [string]$AvrdudePath,
    [string]$Release, # Explicit approval of this release HEX and its adjacent sidecar.
    [switch]$DryRun
)
$ErrorActionPreference='Stop'
function Resolve-Programmer {
    if($AvrdudePath) { return (Resolve-Path -LiteralPath $AvrdudePath).Path }
    $pio=Join-Path $env:USERPROFILE '.platformio/packages'
    if(Test-Path -LiteralPath $pio) {
        foreach($package in Get-ChildItem -LiteralPath $pio -Directory -Filter 'tool-avrdude*') {
            foreach($suffix in @('avrdude.exe','bin/avrdude.exe')) {
                $candidate=Join-Path $package.FullName $suffix
                if(Test-Path -LiteralPath $candidate) { return $candidate }
            }
        }
    }
    $proteus='C:/Program Files (x86)/Labcenter Electronics/Proteus 8 Professional/Tools/ARDUINO/hardware/tools/avr/bin/avrdude.exe'
    if(Test-Path -LiteralPath $proteus) { return $proteus }
    $found=Get-Command avrdude -ErrorAction SilentlyContinue
    if($found) { return $found.Source }
    throw 'avrdude not found in PlatformIO, Proteus or PATH'
}
function Invoke-Programmer([string[]]$Operation) {
    $arguments=$common+$Operation
    Write-Host ('"'+$tool+'" '+(($arguments | ForEach-Object { '"'+$_+'"' }) -join ' '))
    if($DryRun) { return }
    $previous=$ErrorActionPreference; $ErrorActionPreference='Continue'
    try { $reply=& $tool @arguments 2>&1 | ForEach-Object { "$_" }; $code=$LASTEXITCODE }
    finally { $ErrorActionPreference=$previous }
    if($code -ne 0) { throw "avrdude exit $code" }
    return $reply
}
try {
    if($Release) {
        $releasePath=if([IO.Path]::IsPathRooted($Release)) { $Release } else { Join-Path $PSScriptRoot $Release }
        if($PSBoundParameters.ContainsKey('Image')) {
            $selected=if([IO.Path]::IsPathRooted($Image)) { $Image } else { Join-Path $PSScriptRoot $Image }
            if((Resolve-Path -LiteralPath $selected).Path -ne (Resolve-Path -LiteralPath $releasePath).Path) {
                throw '-Image and -Release must identify the same HEX'
            }
        }
        $Image=$releasePath
    }
    $imagePath=if([IO.Path]::IsPathRooted($Image)) { $Image } else { Join-Path $PSScriptRoot $Image }
    if(-not (Test-Path -LiteralPath $imagePath -PathType Leaf)) { throw "Image missing: $imagePath; run build.ps1 first" }
    # Validate even DryRun, before invoking avrdude for any operation.
    $validationArgs=@((Join-Path $PSScriptRoot 'image_metadata.py'),$imagePath,'--json')
    if($Release) { $validationArgs+='--release' }
    $validation=& python @validationArgs 2>&1
    if($LASTEXITCODE) { throw "Image validation failed: $validation" }
    $metadata=($validation -join "`n") | ConvertFrom-Json
    $id=$metadata.identity; $state=if($id.dirty) { 'DIRTY' } else { 'CLEAN' }
    $identity="board $($id.board) $($id.mcu) v$($id.firmware_version) $($id.commit) $state"
    Write-Host "Production identity verified: $identity"
    $format='i'; $tool=Resolve-Programmer
    $common=@('-c','usbasp','-p','m1284p','-B','10')
    $config=Join-Path (Split-Path (Split-Path $tool -Parent) -Parent) 'etc/avrdude.conf'
    if(-not (Test-Path -LiteralPath $config)) { $config=Join-Path (Split-Path $tool -Parent) 'avrdude.conf' }
    if(Test-Path -LiteralPath $config) { $common=@('-C',$config)+$common }
    Write-Host 'ISP -B 10 us = 100 kHz: slow first clock for the factory 1 MHz CPU.'
    # Set EESAVE before chip erase; avrdude verifies each fuse write itself too.
    Invoke-Programmer @('-U','lfuse:w:0xF7:m','-U','hfuse:w:0xC1:m','-U','efuse:w:0xFC:m') | Write-Host
    $expected=@{lfuse=247;hfuse=193;efuse=252}
    foreach($name in @('lfuse','hfuse','efuse')) {
        $reply=Invoke-Programmer @('-q','-q','-U',"${name}:r:-:h")
        if(-not $DryRun) {
            $values=@($reply | Where-Object { $_ -match '^\s*0x[0-9a-fA-F]{1,2}\s*$' })
            $actual=if($values.Count -eq 1) { [Convert]::ToInt32($values[0].Trim(),16) } else { -1 }
            $fuseOk=if($name -eq 'efuse') { $actual -ge 0 -and ($actual -band 7) -eq 4 } else { $actual -eq $expected[$name] }
            if(-not $fuseOk) {
                throw "$name read-back mismatch (expected $('0x{0:X2}' -f $expected[$name]), got $reply)"
            }
        }
    }
    Invoke-Programmer @('-U',"flash:w:${imagePath}:$format") | Write-Host
    Invoke-Programmer @('-U',"flash:v:${imagePath}:$format") | Write-Host
    $approval=if($Release) { 'RELEASE ' } else { '' }
    if($DryRun) { Write-Host "PROGRAM PASS $approval$identity (DRY RUN: commands only; hardware unverified)" }
    else { Write-Host "PROGRAM PASS $approval$identity (flash verified; fuses F7/C1/FC read back)" }
    exit 0
} catch {
    Write-Host "PROGRAM FAIL: $($_.Exception.Message)"
    exit 1
}
