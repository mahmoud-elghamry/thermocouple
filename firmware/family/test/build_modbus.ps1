param([switch]$Gcc)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$include = Join-Path $root 'include'
$out = Join-Path $PSScriptRoot 'modbus/output'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$modules = @(Get-ChildItem -LiteralPath "$root/src/app" -Filter 'modbus*.c' | ForEach-Object { $_.FullName })
$sources = $modules + @("$PSScriptRoot/modbus/test_modbus.c")
$exe = Join-Path $out 'test_modbus.exe'
if ($Gcc) {
    $cc = Get-Command gcc -ErrorAction Stop
    & $cc.Source '-std=c11' '-O0' '-g' '-Wall' '-Wextra' '-Werror' '-fsanitize=address,undefined' "-I$include" @sources '-o' $exe
    if ($LASTEXITCODE -ne 0) { throw 'GCC Modbus compilation failed' }
} else {
    $vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
    $install = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($LASTEXITCODE -ne 0 -or -not $install) { throw 'MSVC Build Tools missing' }
    $dev = Join-Path $install 'Common7/Tools/VsDevCmd.bat'
    $quoted = ($sources | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $cmd = "call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /Zi /fsanitize=address /I`"$include`" $quoted /Fe:`"$exe`" /Fo:`"$out/`" /Fd:`"$out/modbus.pdb`" /link /INCREMENTAL:NO /PDB:`"$out/test_modbus.pdb`""
    $previous = $ErrorActionPreference; $ErrorActionPreference='Continue'
    try { & $env:ComSpec /d /s /c $cmd 2>&1 | ForEach-Object { Write-Host "$_" } }
    finally { $ErrorActionPreference=$previous }
    if ($LASTEXITCODE -ne 0) { throw 'MSVC Modbus compilation failed' }
    $tools=Get-ChildItem -LiteralPath (Join-Path $install 'VC/Tools/MSVC') -Directory | Sort-Object Name -Descending | Select-Object -First 1
    Copy-Item -LiteralPath (Join-Path $tools.FullName 'bin/Hostx64/x64/clang_rt.asan_dynamic-x86_64.dll') -Destination $out -Force
}
& $exe | Tee-Object -FilePath (Join-Path $out 'test-results.txt')
if ($LASTEXITCODE -ne 0) { throw 'Modbus host tests failed' }
$avr = Join-Path $env:USERPROFILE '.platformio/packages/toolchain-atmelavr/bin/avr-gcc.exe'
if (-not (Test-Path -LiteralPath $avr)) {
    $avr='C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\Tools\ARDUINO\hardware\tools\avr\bin\avr-gcc.exe'
}
if (-not (Test-Path -LiteralPath $avr)) { throw 'avr-gcc missing' }
foreach ($src in $modules) {
    $obj=Join-Path $out ((Split-Path $src -Leaf)+'.o')
    & $avr '-std=c11' '-Os' '-mmcu=atmega1284p' '-Wall' '-Wextra' '-Werror' '-fstack-usage' "-I$include" '-c' $src '-o' $obj
    if ($LASTEXITCODE -ne 0) { throw "AVR compile failed: $src" }
}
& (Join-Path (Split-Path $avr) 'avr-size.exe') @($modules | ForEach-Object { Join-Path $out ((Split-Path $_ -Leaf)+'.o') }) | Tee-Object -FilePath "$out/avr-size.txt"
if ($LASTEXITCODE -ne 0) { throw 'AVR size failed' }
& python "$PSScriptRoot/modbus/profile.py" $avr
if ($LASTEXITCODE -ne 0) { throw 'Modbus AVR cycle gate failed' }
Write-Host 'Modbus host tests + strict AVR compilation + cycle gate: PASS'
