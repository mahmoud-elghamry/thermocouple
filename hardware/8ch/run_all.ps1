# Regenerate and re-check the 8-channel board end to end.
#
#   pwsh -File pcb\8ch\run_all.ps1
#
# Every step is idempotent.  Nothing here commits, pushes, or produces
# fabrication data; Gerbers are a separate, deliberate step (see README).

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $here

$kicad = 'C:\Program Files\KiCad\10.0'
$py = Join-Path $kicad 'bin\python.exe'
$cli = Join-Path $kicad 'bin\kicad-cli.exe'
$env:KICAD_CLI = $cli
$env:KICAD10_FOOTPRINT_DIR = Join-Path $kicad 'share\kicad\footprints'
if (-not $env:KICAD_TOOL) {
  $env:KICAD_TOOL = "$env:LOCALAPPDATA\Temp\thermo-kicad-tool-venv\Scripts\kicad-tool.exe"
}

try {
  Write-Output '== 1/8  schematic: symbols, labels, no-connect markers =='
  python populate_schematic.py --labels-only

  Write-Output '== 2/8  ERC =='
  & $cli sch erc --output erc-report.rpt --severity-error --severity-warning `
      thermocouple_8ch.kicad_sch

  Write-Output '== 3/8  netlist =='
  & $cli sch export netlist --output thermocouple_8ch.net thermocouple_8ch.kicad_sch

  Write-Output '== 4/8  design rules into the KiCad project =='
  python apply_rules.py

  Write-Output '== 5/8  schematic -> board parity =='
  & $env:KICAD_TOOL pcb sync thermocouple_8ch.kicad_pcb thermocouple_8ch.kicad_sch `
      --format text | Select-Object -Last 3

  Write-Output '== 6/8  placement, planes, keepouts, chassis ring =='
  & $py generate_board.py

  Write-Output '== 7/8  routing (Freerouting) =='
  & $py route.py --passes 60 --threads 1

  Write-Output '== 8/8  structural checks and DRC =='
  & $py check_board.py
  & $cli pcb drc --output drc-report.rpt --severity-error --severity-warning `
      --schematic-parity thermocouple_8ch.kicad_pcb

  Write-Output ''
  Write-Output 'Reports: erc-report.rpt, drc-report.rpt'
  Write-Output 'Read both before believing anything about this board.'
}
finally {
  Pop-Location
}
