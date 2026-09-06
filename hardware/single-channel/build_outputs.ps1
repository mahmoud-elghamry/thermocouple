$ErrorActionPreference = 'Stop'

$kicadCli = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
$boardFile = Join-Path $PSScriptRoot 'thermocouple_meter.kicad_pcb'
$drcReport = Join-Path $PSScriptRoot 'drc-report.txt'
$gerberDir = Join-Path $PSScriptRoot 'gerbers'
$outputDir = Join-Path $PSScriptRoot 'output'
$zipFile = Join-Path $outputDir 'thermocouple_meter_gerbers.zip'

if (-not (Test-Path -LiteralPath $kicadCli)) {
    throw "KiCad CLI was not found at: $kicadCli"
}

if (-not (Test-Path -LiteralPath $boardFile)) {
    throw "PCB file was not found at: $boardFile"
}

New-Item -ItemType Directory -Force -Path $gerberDir, $outputDir | Out-Null

function Invoke-KiCad {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & $kicadCli @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "KiCad CLI failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

# Do not export fabrication files unless the PCB passes DRC first.
Invoke-KiCad @('pcb', 'drc', $boardFile, '--output', $drcReport, '--exit-code-violations')

Invoke-KiCad @(
    'pcb', 'export', 'gerbers',
    '--output', "$gerberDir\",
    '--layers', 'F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts',
    '--subtract-soldermask',
    '--check-zones',
    $boardFile
)

Invoke-KiCad @(
    'pcb', 'export', 'drill',
    '--output', "$gerberDir\",
    '--format', 'excellon',
    '--excellon-units', 'mm',
    '--excellon-separate-th',
    '--generate-map',
    '--map-format', 'pdf',
    '--generate-report',
    '--report-path', (Join-Path $gerberDir 'drill_report.rpt'),
    $boardFile
)

Invoke-KiCad @(
    'pcb', 'export', 'pos',
    '--output', (Join-Path $outputDir 'positions.csv'),
    '--format', 'csv',
    '--units', 'mm',
    '--side', 'both',
    $boardFile
)

Invoke-KiCad @(
    'pcb', 'export', 'pdf',
    '--output', (Join-Path $outputDir 'thermocouple_meter_layers.pdf'),
    '--layers', 'F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,Edge.Cuts',
    '--mode-multipage',
    '--black-and-white',
    '--check-zones',
    $boardFile
)

Invoke-KiCad @(
    'pcb', 'render',
    '--output', (Join-Path $outputDir 'pcb_top.png'),
    '--side', 'top',
    '--width', '1800',
    '--height', '1000',
    '--quality', 'high',
    '--background', 'opaque',
    '--floor',
    $boardFile
)

Invoke-KiCad @(
    'pcb', 'render',
    '--output', (Join-Path $outputDir 'pcb_bottom.png'),
    '--side', 'bottom',
    '--width', '1800',
    '--height', '1000',
    '--quality', 'high',
    '--background', 'opaque',
    '--floor',
    $boardFile
)

Invoke-KiCad @(
    'pcb', 'render',
    '--output', (Join-Path $outputDir 'pcb_isometric.png'),
    '--side', 'top',
    '--width', '1800',
    '--height', '1000',
    '--quality', 'high',
    '--background', 'opaque',
    '--floor',
    '--perspective',
    '--rotate', '45,0,45',
    $boardFile
)

if (Test-Path -LiteralPath $zipFile) {
    Remove-Item -LiteralPath $zipFile -Force
}

Compress-Archive -Path (Join-Path $gerberDir '*') -DestinationPath $zipFile -CompressionLevel Optimal

Write-Host "DRC report: $drcReport"
Write-Host "Gerbers:    $gerberDir"
Write-Host "Outputs:    $outputDir"
Write-Host "ZIP:        $zipFile"
