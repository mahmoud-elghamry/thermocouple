$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/../..").Path
$out=Join-Path $root 'build/program_test'
New-Item -ItemType Directory -Force $out | Out-Null
$mock=Join-Path $out 'avrdude.ps1'
$image=Join-Path $out 'fixture.hex'
& python "$PSScriptRoot/program_fixtures.py" $out
if($LASTEXITCODE) { throw 'Fixture generation failed' }
@'
Add-Content -LiteralPath $env:F6_PROGRAM_LOG -Value ($args -join ' ')
$global:LASTEXITCODE=0
if($env:F6_PROGRAM_FAIL -eq 'exit') { $global:LASTEXITCODE=3; return }
foreach($name in @('lfuse','hfuse','efuse')) {
    if($args -contains "${name}:r:-:h") {
        if($env:F6_PROGRAM_FAIL -eq $name) { '0x00' }
        elseif($name -eq 'lfuse') { '0xf7' }
        elseif($name -eq 'hfuse') { '0xc1' }
        elseif($env:F6_PROGRAM_FAIL -eq 'masked') { '0x04' }
        else { '0xfc' }
    }
}
'@ | Set-Content -LiteralPath $mock
$env:F6_PROGRAM_LOG=Join-Path $out 'calls.txt'
$checks=0
try {
    foreach($failure in @('','masked','lfuse','hfuse','efuse','exit')) {
        $env:F6_PROGRAM_FAIL=$failure
        Set-Content -LiteralPath $env:F6_PROGRAM_LOG -Value ''
        $result=& powershell -NoProfile -ExecutionPolicy Bypass -File "$root/program.ps1" -AvrdudePath $mock -Image $image 2>&1
        $code=$LASTEXITCODE
        $success=$failure -in @('','masked')
        if(($success -and $code -ne 0) -or (-not $success -and $code -eq 0)) { throw "Unexpected result $failure : $result" }
        $checks++
        $calls=Get-Content -LiteralPath $env:F6_PROGRAM_LOG -Raw
        if($calls -notmatch '-c usbasp -p m1284p -B 10') { throw 'Slow USBasp/m1284p arguments missing' }; $checks++
        if($success) {
            if(($result -join "`n") -notmatch 'PROGRAM PASS .*DIRTY') { throw 'Dirty identity missing from PASS line' }; $checks++
            foreach($expected in @('lfuse:w:0xF7:m','hfuse:w:0xC1:m','efuse:w:0xFC:m','lfuse:r:-:h','hfuse:r:-:h','efuse:r:-:h','flash:v:')) {
                if(-not $calls.Contains($expected)) { throw "Missing $expected" }; $checks++
            }
        }
    }
    foreach($bad in @('tiny.hex','tiny-with-record.hex','old.hex','profile.elf','legacy.hex','other-mcu.hex','missing-record.hex','unpatched.hex','wrong-crc.hex','identity-crc.hex','identity-sidecar.hex','identity-magic.hex','changed.hex','missing.hex','bad-checksum.hex')) {
        $env:F6_PROGRAM_FAIL=''
        Set-Content -LiteralPath $env:F6_PROGRAM_LOG -Value ''
        foreach($dry in @($false,$true)) {
            $extra=@(); if($dry) { $extra=@('-DryRun') }
            $result=& powershell -NoProfile -ExecutionPolicy Bypass -File "$root/program.ps1" -AvrdudePath $mock -Image (Join-Path $out $bad) @extra 2>&1
            if($LASTEXITCODE -eq 0 -or (Get-Content -LiteralPath $env:F6_PROGRAM_LOG -Raw).Trim()) { throw "Unsafe image $bad touched programmer: $result" }; $checks++
        }
    }
    $env:F6_PROGRAM_FAIL=''
    foreach($dry in @($false,$true)) {
        Set-Content -LiteralPath $env:F6_PROGRAM_LOG -Value ''
        $extra=@(); if($dry) { $extra=@('-DryRun') }
        $result=& powershell -NoProfile -ExecutionPolicy Bypass -File "$root/program.ps1" -AvrdudePath $mock -Release (Join-Path $out 'old.hex') @extra 2>&1
        $calls=Get-Content -LiteralPath $env:F6_PROGRAM_LOG -Raw
        if($LASTEXITCODE -ne 0 -or ($result -join "`n") -notmatch 'PROGRAM PASS RELEASE .*CLEAN' -or
           ($dry -and $calls.Trim()) -or (-not $dry -and $calls -notmatch 'flash:v:')) { throw "Approved release failed: $result" }; $checks++
    }
    foreach($bad in @('tiny.hex','legacy.hex','missing-record.hex','identity-crc.hex')) {
        Set-Content -LiteralPath $env:F6_PROGRAM_LOG -Value ''
        $result=& powershell -NoProfile -ExecutionPolicy Bypass -File "$root/program.ps1" -AvrdudePath $mock -Release (Join-Path $out $bad) 2>&1
        if($LASTEXITCODE -eq 0 -or (Get-Content -LiteralPath $env:F6_PROGRAM_LOG -Raw).Trim()) { throw "Release bypassed identity/CRC: $bad : $result" }; $checks++
    }
    Set-Content -LiteralPath $env:F6_PROGRAM_LOG -Value ''
    $result=& powershell -NoProfile -ExecutionPolicy Bypass -File "$root/program.ps1" -AvrdudePath $mock -Image $image -Release (Join-Path $out 'old.hex') 2>&1
    if($LASTEXITCODE -eq 0 -or (Get-Content -LiteralPath $env:F6_PROGRAM_LOG -Raw).Trim()) { throw 'Release authorized a different selected image' }; $checks++
    $result=& powershell -NoProfile -ExecutionPolicy Bypass -File "$root/program.ps1" -AvrdudePath $mock -Image (Join-Path $out 'clean.hex') -DryRun 2>&1
    if($LASTEXITCODE -ne 0 -or ($result -join "`n") -notmatch 'PROGRAM PASS .*CLEAN') { throw "Current clean identity failed: $result" }; $checks++
    $env:F6_PROGRAM_FAIL='exit'
    Set-Content -LiteralPath $env:F6_PROGRAM_LOG -Value ''
    $result=& powershell -NoProfile -ExecutionPolicy Bypass -File "$root/program.ps1" -AvrdudePath $mock -Image $image -DryRun 2>&1
    if($LASTEXITCODE -ne 0 -or (Get-Content -LiteralPath $env:F6_PROGRAM_LOG -Raw).Trim()) { throw "DryRun invoked programmer: $result" }; $checks++
    Write-Host "Programming script: $checks checks PASS (production identity/CRC; fuse masks; mock programmer/DryRun)"
} finally {
    Remove-Item Env:F6_PROGRAM_LOG,Env:F6_PROGRAM_FAIL -ErrorAction SilentlyContinue
}
