param([switch]$Gcc)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$include = Join-Path $root 'include'
# Keep products confined to Lane B's test tree, separate from Lane A build.ps1.
$out = Join-Path $PSScriptRoot 'unit/output_core'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$sources = @(
 'src/services/settings.c','src/services/settings_cal.c','src/services/settings_store.c',
 'src/services/events.c','src/services/fault.c','src/services/tc_math.c','src/services/tc_tables.c',
 'src/app/channel_eval.c','src/app/protection.c','src/app/outputs.c','src/app/outputs_shell.c',
 'test/unit/test_core.c','test/unit/test_settings.c','test/unit/test_events.c',
 'test/unit/test_fault.c','test/unit/test_tc_math.c','test/unit/test_channel_eval.c',
 'test/unit/test_protection.c','test/unit/test_outputs.c','test/scenarios/test_scenarios.c'
) | ForEach-Object { Join-Path $root $_ }
& python (Join-Path $PSScriptRoot 'unit/generate_tc_tables.py') --check
if ($LASTEXITCODE -ne 0) { throw 'TC generated-table verification failed' }
$exe = Join-Path $out 'test_core.exe'
if ($Gcc) {
    $cc = Get-Command gcc -ErrorAction Stop
    & $cc.Source '-std=c11' '-O0' '-g' '-Wall' '-Wextra' '-Werror' '--coverage' `
        '-fsanitize=address,undefined' "-I$include" "-I$PSScriptRoot/unit" @sources '-o' $exe
    if ($LASTEXITCODE -ne 0) { throw 'GCC core compilation failed' }
} else {
    # Same MSVC host setup as firmware/build.ps1.
    $vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
    $install = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($LASTEXITCODE -ne 0 -or -not $install) { throw 'MSVC Build Tools missing' }
    $dev = Join-Path $install 'Common7/Tools/VsDevCmd.bat'
    $quoted = ($sources | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $cmd = "call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /Zi /fsanitize=address /I`"$include`" /I`"$PSScriptRoot/unit`" $quoted /Fe:`"$exe`" /Fo:`"$out/`" /Fd:`"$out/core.pdb`" /link /INCREMENTAL:NO /PDB:`"$out/test_core.pdb`""
    $previous = $ErrorActionPreference; $ErrorActionPreference='Continue'
    try { & $env:ComSpec /d /s /c $cmd 2>&1 | ForEach-Object { Write-Host "$_" } }
    finally { $ErrorActionPreference=$previous }
    if ($LASTEXITCODE -ne 0) { throw 'MSVC core compilation failed' }
    $tools=Get-ChildItem -LiteralPath (Join-Path $install 'VC/Tools/MSVC') -Directory |
        Sort-Object Name -Descending | Select-Object -First 1
    Copy-Item -LiteralPath (Join-Path $tools.FullName 'bin/Hostx64/x64/clang_rt.asan_dynamic-x86_64.dll') -Destination $out -Force
}
& $exe | Tee-Object -FilePath (Join-Path $out 'test-results.txt')
if ($LASTEXITCODE -ne 0) { throw 'Lane B tests failed' }
if ($Gcc) {
    Push-Location $out
    try {
        $notes=Get-ChildItem -LiteralPath $out -Filter '*.gcno' | ForEach-Object { $_.FullName }
        & gcov '-b' '-c' @notes | Tee-Object -FilePath (Join-Path $out 'coverage.txt')
        if ($LASTEXITCODE -ne 0) { throw 'gcov report failed' }
    } finally { Pop-Location }
}
# AVR compile-only enforces the requested GCC warnings and 16-bit-int arithmetic.
$avr = Join-Path $env:USERPROFILE '.platformio/packages/toolchain-atmelavr/bin/avr-gcc.exe'
if (-not (Test-Path -LiteralPath $avr)) {
    $avr='C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\Tools\ARDUINO\hardware\tools\avr\bin\avr-gcc.exe'
}
if (-not (Test-Path -LiteralPath $avr)) { throw 'avr-gcc missing (strict compile gate)' }
foreach ($src in ($sources | Where-Object { $_ -like '*src/*' -or $_ -like '*src\*' })) {
    $obj=Join-Path $out ((Split-Path $src -Leaf)+'.o')
    & $avr '-std=c11' '-Os' '-mmcu=atmega1284p' '-Wall' '-Wextra' '-Werror' "-I$include" '-c' $src '-o' $obj
    if ($LASTEXITCODE -ne 0) { throw "AVR compile failed: $src" }
}
Write-Host 'Lane B host tests + strict AVR compilation: PASS'
