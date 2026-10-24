param([switch]$Gcc)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$include = Join-Path $root 'include'
$out = Join-Path $PSScriptRoot 'ui/output'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$sources = @('src/app/ui.c','src/app/ui_edit.c','src/app/ui_screens.c','src/app/ui_format.c',
 'src/services/settings.c','src/services/fault.c','test/ui/fake_ui.c','test/ui/test_ui.c') |
 ForEach-Object { Join-Path $root $_ }
$exe = Join-Path $out 'test_ui.exe'
if ($Gcc) {
    $cc = Get-Command gcc -ErrorAction Stop
    & $cc.Source '-std=c11' '-O0' '-g' '-Wall' '-Wextra' '-Werror' '-fsanitize=address,undefined' "-I$include" "-I$PSScriptRoot/ui" @sources '-o' $exe
    if ($LASTEXITCODE -ne 0) { throw 'GCC UI compilation failed' }
} else {
    $vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
    $install = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($LASTEXITCODE -ne 0 -or -not $install) { throw 'MSVC Build Tools missing' }
    $dev = Join-Path $install 'Common7/Tools/VsDevCmd.bat'
    $quoted = ($sources | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $installer=Split-Path $vswhere
    $cmd = "set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /Zi /fsanitize=address /I`"$include`" /I`"$PSScriptRoot/ui`" $quoted /Fe:`"$exe`" /Fo:`"$out/`" /Fd:`"$out/ui.pdb`" /link /INCREMENTAL:NO /PDB:`"$out/test_ui.pdb`""
    $previous=$ErrorActionPreference; $ErrorActionPreference='Continue'
    try { & $env:ComSpec /d /s /c $cmd 2>&1 | ForEach-Object { Write-Host "$_" } }
    finally { $ErrorActionPreference=$previous }
    if ($LASTEXITCODE -ne 0) { throw 'MSVC UI compilation failed' }
    $tools=Get-ChildItem -LiteralPath (Join-Path $install 'VC/Tools/MSVC') -Directory | Sort-Object Name -Descending | Select-Object -First 1
    Copy-Item -LiteralPath (Join-Path $tools.FullName 'bin/Hostx64/x64/clang_rt.asan_dynamic-x86_64.dll') -Destination $out -Force
}
& $exe | Tee-Object -FilePath (Join-Path $out 'test-results.txt')
if ($LASTEXITCODE -ne 0) { throw 'UI tests failed' }
$gestureSources=@($sources | Where-Object { $_ -notmatch 'test_ui.c$' }) + @("$root/src/drivers/keys.c","$root/test/ui/test_gestures.c")
$gestureExe=Join-Path $out 'test_gestures.exe'
if($Gcc) {
    & $cc.Source '-std=c11' '-O0' '-g' '-Wall' '-Wextra' '-Werror' '-fsanitize=address,undefined' '-DUI_REAL_KEYS' "-I$include" "-I$PSScriptRoot/ui" @gestureSources '-o' $gestureExe
    if($LASTEXITCODE) { throw 'GCC gestures compilation failed' }
} else {
    $quoted=($gestureSources | ForEach-Object { '"'+$_+'"' }) -join ' '
    $cmd="set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /Zi /fsanitize=address /DUI_REAL_KEYS /I`"$include`" $quoted /Fe:`"$gestureExe`" /Fo:`"$out/`" /Fd:`"$out/gestures.pdb`" /link /INCREMENTAL:NO /PDB:`"$out/test_gestures.pdb`""
    $previous=$ErrorActionPreference;$ErrorActionPreference='Continue'
    try { & $env:ComSpec /d /s /c $cmd 2>&1 | ForEach-Object { Write-Host "$_" } }
    finally { $ErrorActionPreference=$previous }
    if($LASTEXITCODE) { throw 'MSVC gestures compilation failed' }
}
& $gestureExe | Tee-Object -FilePath (Join-Path $out 'gesture-results.txt')
if($LASTEXITCODE) { throw 'UI gesture tests failed' }
$bin='C:/Program Files (x86)/Labcenter Electronics/Proteus 8 Professional/Tools/ARDUINO/hardware/tools/avr/bin'
$avr=Join-Path $bin 'avr-gcc.exe'
if (-not (Test-Path -LiteralPath $avr)) { throw 'avr-gcc missing' }
$objects=@()
foreach ($src in ($sources | Where-Object { $_ -match 'src[/\\]app[/\\]ui' })) {
    $obj=Join-Path $out ((Split-Path $src -Leaf)+'.o'); $objects+=$obj
    & $avr '-std=c11' '-Os' '-fshort-enums' '-Wall' '-Wextra' '-Werror' '-mmcu=atmega1284p' '-DF_CPU=8000000UL' "-I$include" '-fstack-usage' '-c' $src '-o' $obj
    if ($LASTEXITCODE -ne 0) { throw "AVR compile failed: $src" }
}
$sections=& (Join-Path $bin 'avr-size.exe') '-A' @objects
$sections | Tee-Object -FilePath (Join-Path $out 'avr-size.txt')
if ($LASTEXITCODE -ne 0) { throw 'AVR size report failed' }
$ram=0
foreach($line in $sections) { if($line -match '^\.(data|bss|rodata)\s+(\d+)') { $ram+=[int]$Matches[2] } }
if($ram -gt 600) { throw "UI static RAM exceeds 600 bytes: $ram" }
Write-Host "UI static RAM: $ram/600 bytes (app mailbox reused)"
Get-Content "$out/ui*.su" | Set-Content "$out/avr-stack.txt"
Write-Host 'UI host tests + strict AVR compile: PASS'
