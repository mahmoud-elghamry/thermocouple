param([switch]$Gcc)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$include = Join-Path $root 'include'
$out = Join-Path $PSScriptRoot 'acceptance/output'
New-Item -ItemType Directory -Force -Path $out | Out-Null
# Same production link list as build_core.ps1. Never reads either implementer's tests.
$production = @(
 'src/services/settings.c','src/services/settings_cal.c','src/services/settings_store.c',
 'src/services/events.c','src/services/fault.c','src/services/tc_math.c','src/services/tc_tables.c',
 'src/app/channel_eval.c','src/app/protection.c','src/app/outputs.c','src/app/outputs_shell.c'
) | ForEach-Object { Join-Path $root $_ }
$tests = @('runner.c','tables.c','test_accept_protection.c','test_accept_outputs.c','test_accept_settings.c','storage.c','math_events.c') |
    ForEach-Object { Join-Path $PSScriptRoot "acceptance/$_" }
$sources = @($production) + @($tests)
$exe = Join-Path $out 'acceptance.exe'
if ($Gcc) {
    $cc = Get-Command gcc -ErrorAction Stop
    Push-Location $out
    try {
        & $cc.Source '-std=c11' '-O0' '-g' '-Wall' '-Wextra' '-Werror' '--coverage' `
            '-fsanitize=address,undefined' "-I$include" @sources '-o' $exe
        if ($LASTEXITCODE -ne 0) { throw 'GCC acceptance compilation failed' }
    } finally { Pop-Location }
} else {
    $vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
    $install = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($LASTEXITCODE -ne 0 -or -not $install) { throw 'MSVC Build Tools missing' }
    $dev = Join-Path $install 'Common7/Tools/VsDevCmd.bat'
    $quoted = ($sources | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $vswhereDir = Split-Path $vswhere -Parent
    $cmd = "set `"PATH=$vswhereDir;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /Zi /fsanitize=address /I`"$include`" $quoted /Fe:`"$exe`" /Fo:`"$out/`" /Fd:`"$out/acceptance-compiler.pdb`" /link /WX /INCREMENTAL:NO /PDB:`"$out/acceptance.pdb`""
    $previous = $ErrorActionPreference; $ErrorActionPreference='Continue'
    try { & $env:ComSpec /d /s /c $cmd 2>&1 | ForEach-Object { Write-Host "$_" } }
    finally { $ErrorActionPreference=$previous }
    if ($LASTEXITCODE -ne 0) { throw 'MSVC acceptance compilation failed' }
    $tools=Get-ChildItem -LiteralPath (Join-Path $install 'VC/Tools/MSVC') -Directory |
        Sort-Object Name -Descending | Select-Object -First 1
    Copy-Item -LiteralPath (Join-Path $tools.FullName 'bin/Hostx64/x64/clang_rt.asan_dynamic-x86_64.dll') -Destination $out -Force
}
& $exe | Tee-Object -FilePath (Join-Path $out 'test-results.txt')
$testExit = $LASTEXITCODE
if ($Gcc) {
    Push-Location $out
    try {
        $notes=Get-ChildItem -LiteralPath $out -Filter '*.gcno' | ForEach-Object { $_.FullName }
        & gcov '-b' '-c' @notes | Tee-Object -FilePath (Join-Path $out 'coverage.txt')
        if ($LASTEXITCODE -ne 0) { throw 'gcov report failed' }
    } finally { Pop-Location }
}
# Same strict AVR compile-only gate as build_core.ps1, even when assertions fail.
$avr = Join-Path $env:USERPROFILE '.platformio/packages/toolchain-atmelavr/bin/avr-gcc.exe'
if (-not (Test-Path -LiteralPath $avr)) {
    $avr='C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\Tools\ARDUINO\hardware\tools\avr\bin\avr-gcc.exe'
}
if (-not (Test-Path -LiteralPath $avr)) { throw 'avr-gcc missing (strict compile gate)' }
foreach ($src in $production) {
    $obj=Join-Path $out ((Split-Path $src -Leaf)+'.o')
    & $avr '-std=c11' '-Os' '-mmcu=atmega1284p' '-Wall' '-Wextra' '-Werror' "-I$include" '-c' $src '-o' $obj
    if ($LASTEXITCODE -ne 0) { throw "AVR compile failed: $src" }
}
Write-Host 'Strict AVR production compilation: PASS'
if ($testExit -ne 0) { throw 'Lane C acceptance assertions failed; see acceptance/output/test-results.txt' }
Write-Host 'Lane C acceptance: PASS'
