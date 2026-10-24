# Circuit gate; generated files and logs stay in the coordination scratch area.
[CmdletBinding()]
param(
    [string]$Release = 'production/24ch-reva4-20261023-094411-02daef',
    [string]$Python = 'python',
    [string]$PriceCache = ''
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
if (-not [IO.Path]::IsPathRooted($Release)) { $Release = [IO.Path]::GetFullPath((Join-Path $repo $Release)) }
$cli = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
# No pcbnew step is needed; KiCad's python.exe is deliberately not used.
$results = [ordered]@{}
$oldCli = $env:KICAD_CLI
$oldOut = $env:THERMO24_SCH_OUT
$oldBytecode = $env:PYTHONDONTWRITEBYTECODE
$run = Join-Path $repo ('hardware\8ch-new\output\coord\family-gates\gate-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))

function Get-HardwareHashes {
    $hashes = @{}
    Get-ChildItem -LiteralPath (Join-Path $repo 'hardware\24ch') -Recurse -File -Force |
        ForEach-Object { $hashes[$_.FullName] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
    return $hashes
}

function Invoke-Step([string]$Name, [string[]]$Arguments) {
    $log = Join-Path $run ($Name + '.log')
    Write-Host "`n=== $Name ==="
    Write-Host ('python -B ' + ($Arguments -join ' '))
    # Native stderr is logged; a nonzero exit is a recorded gate failure.
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Python -B @Arguments 2>&1 | Tee-Object -FilePath $log | Out-Host
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
    $results[$Name] = ($code -eq 0)
    Write-Host "$Name exit=$code"
    return ($code -eq 0)
}

try {
    if (-not (Test-Path -LiteralPath $cli -PathType Leaf)) { throw "Missing KiCad CLI: $cli" }
    foreach ($f in 'netlist.xml','BOM.csv','DNP.txt','MANIFEST.txt') {
        if (-not (Test-Path -LiteralPath (Join-Path $Release $f) -PathType Leaf)) { throw "Missing release input $f" }
    }
    $Python = (Get-Command $Python -ErrorAction Stop).Source
    if ($Python -eq 'C:\Program Files\KiCad\10.0\bin\python.exe') {
        throw 'Use ordinary Python: this circuit gate does not need pcbnew.'
    }
    New-Item -ItemType Directory -Path $run -Force -ErrorAction Stop | Out-Null
    $before = Get-HardwareHashes
    $env:KICAD_CLI = $cli
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $out24 = Join-Path $run '24'
    $out8 = Join-Path $run '8'
    $out40 = Join-Path $run '40'
    $original = Join-Path $run 'original24'
    $build = Join-Path $PSScriptRoot 'build.py'
    $compare = Join-Path $PSScriptRoot 'compare_release.py'
    $null = Invoke-Step 'pure-python' @((Join-Path $PSScriptRoot 'test_family.py'))
    $null = Invoke-Step 'profiles-and-8l' @((Join-Path $repo 'hardware\family\tools\test_profiles.py'))
    $null = Invoke-Step 'release-text-and-8l' @((Join-Path $repo 'hardware\family\tools\test_docs_new.py'))
    $env:THERMO24_SCH_OUT = $original
    $null = Invoke-Step 'original-build24' @((Join-Path $repo 'hardware\24ch\gen\build.py'))
    $env:THERMO24_SCH_OUT = $oldOut
    $originalEqual = Invoke-Step 'original-compare' @($compare, $original, $Release)
    if (-not $originalEqual) {
        Write-Host 'ORIGINAL BASELINE FAILURE: original generator differs from release or comparison could not run; see original-compare.log.'
    }
    $null = Invoke-Step 'family-build24' @($build, '24', '--out', $out24)
    $familyEqual = Invoke-Step 'family-compare' @($compare, $out24, $Release)
    if ($familyEqual -and $originalEqual) {
        $null = Invoke-Step 'family-build8' @($build, '8', '--out', $out8)
        $null = Invoke-Step 'family-build40' @($build, '40', '--out', $out40)
        $null = Invoke-Step 'fault-proof' @((Join-Path $PSScriptRoot 'fault_proof.py'), (Join-Path $run 'faults'), $Release)
        $costArgs = @((Join-Path $PSScriptRoot 'cost.py'), (Join-Path $out8 'thermo8.xml'))
        if ($PriceCache) { $costArgs += @('--cache', $PriceCache) }
        $null = Invoke-Step 'offline-cost8' $costArgs
    } else {
        $results['family-build8'] = $false
        $results['family-build40'] = $false
        $results['fault-proof'] = $false
        Write-Host 'STOP: release equivalence was not established. Gate B and fault proof skipped; no comparison rules changed.'
    }
    $null = Invoke-Step 'check-docs' @((Join-Path $repo 'docs\check_docs.py'))
    $after = Get-HardwareHashes
    $changed = @($before.Keys | Where-Object { -not $after.ContainsKey($_) -or $after[$_] -ne $before[$_] })
    $changed += @($after.Keys | Where-Object { -not $before.ContainsKey($_) })
    $results['hardware24-byte-identical'] = ($changed.Count -eq 0)
    foreach ($path in $changed) { Write-Host "CHANGED hardware/24ch: $path" }
} catch {
    Write-Host "GATE TOOL FAILURE: $($_.Exception.Message)"
    $results['tool-execution'] = $false
} finally {
    $env:KICAD_CLI = $oldCli
    $env:THERMO24_SCH_OUT = $oldOut
    $env:PYTHONDONTWRITEBYTECODE = $oldBytecode
}

$summary = @('FAMILY GATE SUMMARY')
foreach ($name in $results.Keys) {
    $status = if ($results[$name]) { 'PASS' } else { 'FAIL' }
    $summary += "$name`: $status"
}
$passed = $results.Count -gt 0 -and @($results.Values | Where-Object { -not $_ }).Count -eq 0
$verdict = if ($passed) { 'PASS' } else { 'FAIL' }
$summary += "FAMILY GATES: $verdict"
$summary += "Reports: $run"
$summary | ForEach-Object { Write-Host $_ }
if (Test-Path -LiteralPath $run) { $summary | Set-Content -LiteralPath (Join-Path $run 'gate-summary.txt') -Encoding UTF8 }
if ($passed) { exit 0 } else { exit 1 }
