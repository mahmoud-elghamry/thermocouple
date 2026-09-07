# Program a THERMO-8CH unit: fuses first, then flash, both verified.
#
#   powershell -File firmware\program.ps1
#   powershell -File firmware\program.ps1 -Programmer avrisp2 -Port COM3
#
# WHICH IMAGE MATTERS. build/ holds four, and two of them drive PB3 with
# OPPOSITE meanings:
#
#   thermo_8ch_max31856.hex    the eight-channel board.  PB3 HIGH = safe to
#                              run (energised-to-run permit).  THIS ONE.
#   thermo_8ch_max6675_sim.hex the same application against Proteus MAX6675
#                              models.  Simulation only, wrong converter.
#   legacy_1ch_*.hex           the superseded single-channel board.  PB3 HIGH
#                              = over-temperature ALARM - the inverse.
#
# Flashing a legacy image onto the eight-channel board inverts the safety
# function silently: the machine runs when hot and stops when cold.  There is
# no symptom until it matters (I-031).
#
# Fuse values and the reasoning behind them: firmware/fuses.md

[CmdletBinding()]
param(
    [string]$Programmer = 'usbasp',
    [string]$Port,
    [string]$Image = 'build\thermo_8ch_max31856.hex',
    [string]$LowFuse = '0x24',
    [string]$HighFuse = '0xD1',
    # Read the unit's current state and stop, changing nothing.
    [switch]$ReadOnly
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$imagePath = if ([System.IO.Path]::IsPathRooted($Image)) {
    $Image
} else {
    Join-Path $root $Image
}

# Returns the exe plus, for the Proteus-bundled copy, the -C argument it needs.
# That build ships without a compiled-in config path and exits with
# "can't open config file" unless it is told where avrdude.conf is.
function Resolve-Avrdude {
    $onPath = Get-Command 'avrdude' -ErrorAction SilentlyContinue
    if ($onPath) { return @{ Exe = $onPath.Source; ConfigArgs = @() } }

    $avrRoot = 'C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\Tools\ARDUINO\hardware\tools\avr'
    $bundled = Join-Path $avrRoot 'bin\avrdude.exe'
    $bundledConf = Join-Path $avrRoot 'etc\avrdude.conf'
    if (Test-Path -LiteralPath $bundled) {
        if (-not (Test-Path -LiteralPath $bundledConf)) {
            throw "Found $bundled but not its config at $bundledConf."
        }
        return @{ Exe = $bundled; ConfigArgs = @('-C', $bundledConf) }
    }

    throw @'
avrdude not found.

Looked on PATH and in the Proteus-bundled AVR toolchain at
  C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\Tools\ARDUINO\hardware\tools\avr\bin\

Install avrdude, or point this script at it. Nothing was changed.
'@
}

$resolved = Resolve-Avrdude
$avrdude = $resolved.Exe
$common = $resolved.ConfigArgs + @('-c', $Programmer, '-p', 'm32')
if ($Port) { $common += @('-P', $Port) }

# Windows PowerShell turns a native tool's stderr into error records, and with
# ErrorActionPreference = Stop that buries our own message under a stack trace.
# avrdude writes all its progress to stderr, so every call goes through here and
# is judged on its exit code, which this script checks at each call site.
function Invoke-Avrdude {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $avrdude @args 2>&1 | ForEach-Object { "$_" }
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Read-Fuse([string]$name) {
    $value = Invoke-Avrdude @common '-q' '-q' '-U' "${name}:r:-:h"
    if ($LASTEXITCODE -ne 0) {
        throw ("Could not read $name (avrdude exit $LASTEXITCODE). " +
               'Is the programmer connected and the unit powered?')
    }
    $first = $value | Where-Object { $_ -match '^0x' } | Select-Object -First 1
    if (-not $first) {
        throw "Could not parse $name from avrdude output: $value"
    }
    return $first.Trim()
}

Write-Host "avrdude:    $avrdude"
Write-Host "programmer: $Programmer$(if ($Port) { " on $Port" })"
Write-Host ''

# --- 1. Read and show what is on the unit now, before touching anything ------
Write-Host 'Current fuses:'
$currentLow = Read-Fuse 'lfuse'
$currentHigh = Read-Fuse 'hfuse'
$currentLock = Read-Fuse 'lock'
Write-Host "  low  $currentLow"
Write-Host "  high $currentHigh"
Write-Host "  lock $currentLock"
Write-Host ''

if ($currentLock -notin @('0xff', '0xFF')) {
    Write-Warning "Lock bits are $currentLock, not 0xff. Programming may fail or verify incorrectly."
}

if ($ReadOnly) {
    Write-Host 'Read-only: nothing was changed.'
    exit 0
}

# --- 2. The image has to exist before the unit is disturbed ------------------
if (-not (Test-Path -LiteralPath $imagePath)) {
    throw @"
Image not found: $imagePath

Build it first:
  powershell -File firmware\build.ps1

Nothing was changed on the unit.
"@
}
Write-Host "image:      $imagePath"
if ((Split-Path $imagePath -Leaf) -notlike 'thermo_8ch_max31856*') {
    Write-Warning 'This is NOT the eight-channel MAX31856 image. Read the header of this script before continuing.'
}
Write-Host ''

# --- 3. Fuses, then read back and refuse to lie about the result ------------
Write-Host "Writing fuses: low $LowFuse, high $HighFuse"
Invoke-Avrdude @common '-U' "lfuse:w:${LowFuse}:m" '-U' "hfuse:w:${HighFuse}:m" |
    Write-Host
if ($LASTEXITCODE -ne 0) { throw 'Fuse write failed.' }

$verifyLow = Read-Fuse 'lfuse'
$verifyHigh = Read-Fuse 'hfuse'
if ([convert]::ToInt32($verifyLow, 16) -ne [convert]::ToInt32($LowFuse, 16)) {
    throw "Low fuse read back as $verifyLow, expected $LowFuse. The unit is NOT correctly configured."
}
if ([convert]::ToInt32($verifyHigh, 16) -ne [convert]::ToInt32($HighFuse, 16)) {
    throw "High fuse read back as $verifyHigh, expected $HighFuse. The unit is NOT correctly configured."
}
Write-Host "Fuses verified: low $verifyLow, high $verifyHigh"
Write-Host ''

# --- 4. Flash, with avrdude's own verify pass -------------------------------
Write-Host 'Flashing...'
Invoke-Avrdude @common '-U' "flash:w:${imagePath}:i" | Write-Host
if ($LASTEXITCODE -ne 0) { throw 'Flash write or verification failed.' }

Write-Host ''
Write-Host 'Programmed and verified.'
Write-Host ''
Write-Host 'Record for the commissioning sheet:'
Write-Host "  low fuse   $verifyLow"
Write-Host "  high fuse  $verifyHigh"
Write-Host "  lock bits  $currentLock"
Write-Host "  image      $(Split-Path $imagePath -Leaf)"
Write-Host '  version    read it off the LCD at boot'
Write-Host ''
Write-Host 'A unit with a blank EEPROM shows SET SETPOINT and will not permit'
Write-Host 'running until an operator stores a setpoint. That is expected.'
