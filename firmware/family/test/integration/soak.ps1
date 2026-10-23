param([uint32]$Days=60,[uint32]$Minutes=0,[switch]$ClockTest,[switch]$WrapTest,[switch]$CompileOnly)
$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/../..").Path
$variant=if($ClockTest) { 'clock' } elseif($WrapTest) { 'wrap' } elseif($Minutes) { 'smoke' } else { 'full' }
$out=Join-Path $root "test/integration/output_soak/$variant"
New-Item -ItemType Directory -Force $out | Out-Null
$vswhere='C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe'
$install=& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$dev=Join-Path $install 'Common7/Tools/VsDevCmd.bat'
$sources=Get-Content "$root/sources/hardware_host.txt" | Where-Object { $_ -and $_ -notmatch '^test/(unit|integration/test_)' } | ForEach-Object { '"'+(Join-Path $root $_)+'"' }
$sources+='"'+(Join-Path $PSScriptRoot 'test_soak.c')+'"'
$response=Join-Path $out 'sources.rsp'
[IO.File]::WriteAllText($response,($sources -join ' '))
$installer=Split-Path $vswhere
$exe=Join-Path $out 'soak.exe'
$command="set `"PATH=$installer;%PATH%`" && call `"$dev`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /O2 /GL /DFAMILY_TEST /D_CRT_SECURE_NO_WARNINGS /I`"$root/include`" /I`"$root/test/fakes`" @`"$response`" /Fe:`"$exe`" /Fo:`"$out/`" /link /LTCG"
& $env:ComSpec /d /s /c $command
if($LASTEXITCODE) { throw 'Soak compilation failed' }
if($CompileOnly) { exit 0 }
$watch=[Diagnostics.Stopwatch]::StartNew()
$arguments=@("$Days","$Minutes"); if($ClockTest) { $arguments=@('--clock-test') }
if($WrapTest) { $arguments=@('--wrap-test') }
& $exe @arguments | Tee-Object -FilePath "$out/results.txt"
$code=$LASTEXITCODE
$watch.Stop(); Write-Host ('Soak wall time: {0:N2} seconds' -f $watch.Elapsed.TotalSeconds)
if($code) { throw "Soak failed ($code)" }
