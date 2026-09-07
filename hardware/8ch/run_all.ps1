# Validate the frozen board by default. -Regenerate rewrites the whole board
# and is only for a revision whose regeneration the owner has authorized.
#
#   pwsh -File hardware\8ch\run_all.ps1
#
# Every step is idempotent.  Nothing here commits, pushes, or produces
# fabrication data; Gerbers are a separate, deliberate step (see README).

[CmdletBinding()]
param([switch]$Regenerate, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$here/check_commands.ps1"
if (-not $Regenerate) {
  & "$here/validate.ps1" -OutputDirectory $OutputDirectory
  return
}
if (Get-Process pcbnew,eeschema -ErrorAction SilentlyContinue) {
  throw 'Close KiCad editors before regenerating: they can overwrite this work.'
}
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
  Invoke-CheckedNative 'python' @('populate_schematic.py', '--labels-only')

  Write-Output '== 2/8  ERC =='
  Invoke-CheckedNative $env:KICAD_TOOL @('sch', 'erc', 'thermocouple_8ch.kicad_sch', '-o', 'erc-report.rpt') -AllowedExitCodes @(0,5)
  Assert-ErcReport 'erc-report.rpt'

  Write-Output '== 3/8  netlist =='
  Invoke-CheckedNative $env:KICAD_TOOL @('sch', 'netlist', 'thermocouple_8ch.kicad_sch', '-o', 'thermocouple_8ch.net')
  Invoke-CheckedNative 'python' @('netlist_fingerprint.py', 'netlist-baseline-reva0.json', 'thermocouple_8ch.net')

  Write-Output '== 4/8  design rules into the KiCad project =='
  Invoke-CheckedNative 'python' @('apply_rules.py')

  Write-Output '== 5/8  schematic -> board parity =='
  Invoke-CheckedNative $env:KICAD_TOOL @('pcb', 'sync', 'thermocouple_8ch.kicad_pcb', 'thermocouple_8ch.kicad_sch')

  Write-Output '== 6/8  placement, planes, keepouts, chassis ring =='
  Invoke-CheckedNative $py @('generate_board.py')

  Write-Output '== 7/8  routing (Freerouting) =='
  Invoke-CheckedNative $py @('route.py', '--passes', '60', '--threads', '1')

  Write-Output '== 8/8  structural checks and DRC =='
  Invoke-CheckedNative $py @('check_board.py')
  Invoke-CheckedNative $env:KICAD_TOOL @('pcb', 'drc', 'thermocouple_8ch.kicad_pcb', '-o', 'drc-report.rpt')
  Assert-DrcReport 'drc-report.rpt'

  Write-Output ''
  Write-Output 'Reports: erc-report.rpt, drc-report.rpt'
  Write-Output 'Read both before believing anything about this board.'
}
finally {
  Pop-Location
}
