# Preserved review reproductions — 2026-09-29

These source files preserve I-073 and I-074 outside ignored `production/`.
They include the current real application source using relative paths. They
are diagnostic reproductions, **not additional passing release gates** and
are deliberately not linked by `firmware/build.ps1` or the Makefile yet.
When fixing the issues, integrate the relevant cases into the normal tests
without retaining duplicate test plumbing indefinitely.

| Source | What is real / modeled | Historical result on reviewed firmware |
|---|---|---|
| `repro_save_ack.c` | Real application/protection/settings/monitor; HAL doubles | Exit 1, seven failed safety assertions. Stored limit 100 C, first save fails at tick 11, inputs change 90 to 120 C at tick 15, successful retry at 23, ACK at 24. RUN_PERMIT is wrongly on at ticks 24–30. A fix must keep it off while hot or invalid and allow normal safe recovery. |
| `repro_boot.c` | Real application **and** MAX31856 bank driver; SPI register model | Exit 0 **confirms the old defect**, not safe behavior: eight healthy 20 C inputs, stored 100 C limit, false CH1 FAULT persists through tick 19 and ACK clears it at 20. Rewrite these behavior assertions for the explicitly chosen startup policy when fixing I-074. |

Both were compiled with MSVC C11 `/W4 /WX` and rerun after relocation on
2026-09-29. Output is in
`production/review-20260929/preserved-reproductions/` (ignored).
Loop ticks are simulated iterations, not measured physical milliseconds.

## Windows reproduction

Run from the repository root in PowerShell with the same installed Visual
Studio C build tools used by `firmware/build.ps1`. No AVR programmer or
physical board is involved. This is the compile/run sequence exercised in
the review; inspect each executable's exit code using the table above.

```powershell
$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
$vsInstall = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vsDevCmd = Join-Path $vsInstall 'Common7\Tools\VsDevCmd.bat'
$reproOutput = Join-Path (Get-Location) 'production\review-20260929\preserved-reproductions'
New-Item -ItemType Directory -Path $reproOutput -Force | Out-Null
$common = 'firmware\src\app\protection.c firmware\src\app\sensor_monitor.c firmware\src\app\settings.c'
foreach ($case in @('repro_save_ack', 'repro_boot')) {
    $extra = if ($case -eq 'repro_boot') { 'firmware\src\hal\temperature_max31856_bank.c firmware\src\hal\tc_decode.c' } else { '' }
    $compile = "call `"$vsDevCmd`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /Ifirmware\tests\host_mocks /Ifirmware\include firmware\tests\reproductions\$case.c $common $extra /Fe:`"$reproOutput\$case.exe`" /Fo:`"$reproOutput\\`""
    & $env:ComSpec /d /s /c $compile
    if ($LASTEXITCODE -ne 0) { throw "Compilation failed for $case" }
    & "$reproOutput\$case.exe"
    Write-Output "$case exit code: $LASTEXITCODE"
}
```

## Evidence preservation

The production-folder logs and binaries can be regenerated. Keep these
sources and the issue descriptions when committing the review; no commit
was made by the review agent. Original artifact copies remain untouched.
Hardware measurements are not simulated by these tests.
