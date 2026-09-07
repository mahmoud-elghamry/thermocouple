# Validate a fresh snapshot; kicad-tool refills zones on the COPY only.
[CmdletBinding()]
param([string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/check_commands.ps1"
$repoRoot = (Resolve-Path "$PSScriptRoot/../..").Path
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot ('production/validation-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,6))
}
$out = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $out) { throw "Use a new output directory to prevent stale reports: $out" }
New-Item -ItemType Directory -Path $out | Out-Null
# Windows PowerShell 5.1 will not bind plain strings from the pipeline to
# Get-FileHash, so `$inputs | Get-FileHash` silently produced nothing here.
# Both the before and after lists came back empty, Compare-Object found no
# difference between two empty sets, and the script reported "Sources
# unchanged" without ever having hashed anything - a gate claiming a check it
# did not perform, which is worse than one that fails. Hash by LiteralPath and
# refuse to report success on an empty result.
function Get-SourceHashes([string[]]$Paths) {
    $hashes = foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Missing source file: $path" }
        Get-FileHash -LiteralPath $path -Algorithm SHA256 | Select-Object Path, Hash
    }
    $hashes = @($hashes)
    if ($hashes.Count -ne $Paths.Count) {
        throw "Hashed $($hashes.Count) of $($Paths.Count) source files; cannot vouch for them."
    }
    return $hashes
}

$snapshot = Join-Path $out 'snapshot'
New-Item -ItemType Directory -Path $snapshot | Out-Null
$stem = 'thermocouple_8ch'
$inputs = @('.kicad_sch', '.kicad_pcb', '.kicad_pro', '.kicad_dru') | ForEach-Object { Join-Path $PSScriptRoot ($stem + $_) }
$before = Get-SourceHashes $inputs
foreach ($inputFile in $inputs) { Copy-Item -LiteralPath $inputFile -Destination $snapshot }
foreach ($table in @('fp-lib-table','sym-lib-table')) {
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot $table)) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $table) -Destination $snapshot
    }
}
$tool = $env:KICAD_TOOL
if (-not $tool) { $tool = "$env:LOCALAPPDATA/Temp/thermo-kicad-tool-venv/Scripts/kicad-tool.exe" }
if (-not $env:KICAD_CLI) { $env:KICAD_CLI = 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' }
$sch = Join-Path $snapshot "$stem.kicad_sch"
$pcb = Join-Path $snapshot "$stem.kicad_pcb"
$erc = Join-Path $out 'erc-report.rpt'
$drc = Join-Path $out 'drc-report.rpt'
$net = Join-Path $out 'current.net'
# KiCad exit 5 means violations, including warnings. Parse the fresh report
# below to allow known warnings while rejecting every electrical error.
Invoke-CheckedNative $tool @('sch','erc',$sch,'-o',$erc) -AllowedExitCodes @(0,5)
Assert-ErcReport $erc
Invoke-CheckedNative $tool @('sch','netlist',$sch,'-o',$net)
Invoke-CheckedNative 'python' @((Join-Path $PSScriptRoot 'netlist_fingerprint.py'), (Join-Path $PSScriptRoot 'netlist-baseline-reva0.json'), $net)
Invoke-CheckedNative $tool @('pcb','drc',$pcb,'-o',$drc)
Assert-DrcReport $drc
$after = Get-SourceHashes $inputs
if (Compare-Object $before $after -Property Path,Hash) { throw 'Source hardware changed while validation ran; discard this result.' }
@{ created = (Get-Date -Format o); sourceFiles = $before; erc = $erc; drc = $drc; netlist = $net; sourceUnchanged = $true } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'validation.json') -Encoding UTF8
Write-Output "Snapshot validation passed. Sources unchanged. Reports: $out"

# Explicit success exit: the last native call above is kicad-cli, whose exit
# code leaks through and can be nonzero for warnings that Assert-* already
# judged as acceptable.
exit 0
