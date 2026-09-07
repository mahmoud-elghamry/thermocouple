# Fault injection for the native-command and report gates; never loads a PCB.
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/check_commands.ps1"
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('thermo-gates-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
$passed = 0
function Assert-Rejected([scriptblock]$Action) {
    $rejected = $false
    try { & $Action | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw 'Gate accepted an injected failure.' }
    $script:passed++
}
# Explicitly establish that execution never reaches the stage after failure.
$script:continued = $false
try {
    Invoke-CheckedNative (Get-Process -Id $PID).Path @('-NoProfile','-Command','exit 17')
    $script:continued = $true
} catch {}
if ($continued) { throw 'Native failure did not stop the pipeline.' }
$passed++
$erc = Join-Path $tempRoot 'erc.rpt'
'** ERC messages: 172 Errors 1 Warnings 171' | Set-Content $erc
Assert-Rejected { Assert-ErcReport $erc }
'** ERC messages: 171 Errors 0 Warnings 171' | Set-Content $erc
Assert-ErcReport $erc
$passed++
$drc = Join-Path $tempRoot 'drc.rpt'
@'
** Found 1 DRC violations **
[clearance]: injected
    Rule: clearance; error
** Found 0 unconnected pads **
** Found 0 Footprint errors **
'@ | Set-Content $drc
Assert-Rejected { Assert-DrcReport $drc }
(Get-Content $drc -Raw).Replace('; error', '; warning') | Set-Content $drc
Assert-DrcReport $drc
$passed++
(Get-Content $drc -Raw).Replace('Found 0 unconnected', 'Found 1 unconnected') | Set-Content $drc
Assert-Rejected { Assert-DrcReport $drc }
'** Found 0 DRC violations **`n** Found 0 unconnected pads **`n** Found 1 Footprint errors **'.Replace('`n', "`n") | Set-Content $drc
Assert-Rejected { Assert-DrcReport $drc }
'partial output' | Set-Content $drc
Assert-Rejected { Assert-DrcReport $drc }
Write-Output "Hardware gate fault injection: $passed checks passed. Fixtures: $tempRoot"
