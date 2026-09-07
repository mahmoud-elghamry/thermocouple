# Firmware build and host tests.
#
# The source lists come from sources/*.txt, which the Makefile reads as well.
# Neither build system carries its own copy of the list any more (I-022).

$ErrorActionPreference = 'Stop'

$avrRoot = 'C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\Tools\ARDUINO\hardware\tools\avr'
$gcc = Join-Path $avrRoot 'bin\avr-gcc.exe'
$objcopy = Join-Path $avrRoot 'bin\avr-objcopy.exe'
$size = Join-Path $avrRoot 'bin\avr-size.exe'
$include = Join-Path $PSScriptRoot 'include'
$build = Join-Path $PSScriptRoot 'build'
$sources = Join-Path $PSScriptRoot 'sources'
$hostMocks = Join-Path $PSScriptRoot 'tests\host_mocks'

New-Item -ItemType Directory -Path $build -Force | Out-Null

# Fails if a source list names a missing file, or a src/*.c file is in no
# list at all - the second half is what would have caught I-030 (I-022,
# I-042).
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) { throw 'python not found; cannot run sources/check_lists.py' }
& $python.Source (Join-Path $sources 'check_lists.py')
if ($LASTEXITCODE -ne 0) { throw 'Source list check failed (I-022, I-042).' }

# Remove only generated firmware products, never source files.
Get-ChildItem -LiteralPath $build -File -Recurse | Where-Object {
    $_.Extension -in @('.o', '.elf', '.hex')
} | Remove-Item -Force

$commonFlags = @(
    '-std=c11', '-Os', '-Wall', '-Wextra', '-Werror', '-mmcu=atmega32',
    '-DF_CPU=8000000UL', "-I$include", '-ffunction-sections', '-fdata-sections'
)

function Get-SourceList([string]$name) {
    $path = Join-Path $sources "$name.txt"
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing source list: $path" }
    Get-Content -LiteralPath $path | ForEach-Object { ($_ -replace '#.*', '').Trim() } |
        Where-Object { $_ -ne '' }
}

# $variant keeps two object files apart when the same source is compiled twice
# with different flags (the Proteus SPI mode).
function Compile-List([string[]]$relativeSources, [string[]]$extraFlags, [string]$variant) {
    $objects = @()
    foreach ($relative in $relativeSources) {
        $sourcePath = Join-Path $PSScriptRoot (Join-Path 'src' $relative)
        $objectName = ($relative -replace '[\\/]', '_') -replace '\.c$', ''
        if ($variant) { $objectName = "$objectName.$variant" }
        $objectPath = Join-Path $build "$objectName.o"
        & $gcc @commonFlags @extraFlags '-c' $sourcePath '-o' $objectPath
        if ($LASTEXITCODE -ne 0) { throw "Compilation failed: $relative" }
        $objects += $objectPath
    }
    return $objects
}

$baseObjects       = Compile-List (Get-SourceList 'base')             @() ''
$app8chObjects     = Compile-List (Get-SourceList 'app_8ch')          @() ''
$bank31856Objects  = Compile-List (Get-SourceList 'bank_max31856')    @() ''
$appLegacyObjects  = Compile-List (Get-SourceList 'app_legacy')       @() ''
$sensor31856Object = Compile-List (Get-SourceList 'sensor_max31856')  @() ''
$sensor6675Object  = Compile-List (Get-SourceList 'sensor_max6675')   @() ''
$bankSimObjects    = Compile-List (Get-SourceList 'bank_max6675') `
    @('-DHAL_MAX6675_SPI_MODE=MCAL_SPI_MODE_1') 'sim'

function Link-Image([string]$name, [string[]]$objects) {
    $elf = Join-Path $build "$name.elf"
    $hex = Join-Path $build "$name.hex"
    & $gcc '-mmcu=atmega32' '-Wl,--gc-sections' @objects '-o' $elf
    if ($LASTEXITCODE -ne 0) { throw "Linking failed: $name" }
    & $objcopy '-O' 'ihex' '-R' '.eeprom' $elf $hex
    if ($LASTEXITCODE -ne 0) { throw "HEX generation failed: $name" }
    return $elf
}

$images = [ordered]@{
    'thermo_8ch_max31856'   = $baseObjects + $app8chObjects + $bank31856Objects
    'thermo_8ch_max6675_sim' = $baseObjects + $app8chObjects + $bankSimObjects
    'legacy_1ch_max31856'   = $baseObjects + $appLegacyObjects + $sensor31856Object
    'legacy_1ch_max6675'    = $baseObjects + $appLegacyObjects + $sensor6675Object
}

$builtElfs = [ordered]@{}
foreach ($image in $images.GetEnumerator()) {
    $builtElfs[$image.Key] = Link-Image $image.Key $image.Value
}

foreach ($image in $builtElfs.GetEnumerator()) {
    Write-Host ''
    Write-Host "$($image.Key):"
    & $size '-C' '--mcu=atmega32' $image.Value
    if ($LASTEXITCODE -ne 0) { throw "Size report failed: $($image.Key)" }
}

# --- Host tests ---------------------------------------------------------------
$hostBuild = Join-Path $build 'host_tests'
$testExe = Join-Path $hostBuild 'test_app_logic.exe'
$testSource = Join-Path $PSScriptRoot 'tests\test_app_logic.c'
$hostSources = Get-SourceList 'host_test' | ForEach-Object {
    Join-Path $PSScriptRoot (Join-Path 'src' $_)
}
$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw 'Visual Studio Build Tools not found; cannot run host logic tests.'
}
$vsInstall = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($vsInstall)) {
    throw 'MSVC C compiler not found; cannot run host logic tests.'
}
$vsDevCmd = Join-Path $vsInstall 'Common7\Tools\VsDevCmd.bat'
New-Item -ItemType Directory -Path $hostBuild -Force | Out-Null
$quotedSources = ($hostSources | ForEach-Object { "`"$_`"" }) -join ' '
$compileCommand = "call `"$vsDevCmd`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /I`"$include`" `"$testSource`" $quotedSources /Fe:`"$testExe`" /Fo:$hostBuild\"
& $env:ComSpec /d /s /c $compileCommand
if ($LASTEXITCODE -ne 0) { throw 'Application logic test compilation failed.' }
& $testExe
if ($LASTEXITCODE -ne 0) { throw "Application logic tests failed: $LASTEXITCODE" }

# --- Host integration tests (I-042) --------------------------------------------
# Runs main_8ch.c itself against HAL doubles (AVR headers resolved to
# tests/host_mocks/), and the MAX31856 bank driver against a register model.
function Run-HostIntegrationTest([string]$name, [string]$listName,
    [string[]]$extraIncludes) {
    $exe = Join-Path $hostBuild "$name.exe"
    $source = Join-Path $PSScriptRoot "tests\$name.c"
    $extraSources = Get-SourceList $listName | ForEach-Object {
        Join-Path $PSScriptRoot (Join-Path 'src' $_)
    }
    $quoted = ($extraSources | ForEach-Object { "`"$_`"" }) -join ' '
    $includeFlags = ($extraIncludes | ForEach-Object { "/I`"$_`"" }) -join ' '
    $cmd = "call `"$vsDevCmd`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX $includeFlags /I`"$include`" `"$source`" $quoted /Fe:`"$exe`" /Fo:$hostBuild\"
    & $env:ComSpec /d /s /c $cmd
    if ($LASTEXITCODE -ne 0) { throw "$name compilation failed." }
    & $exe
    if ($LASTEXITCODE -ne 0) { throw "$name failed: $LASTEXITCODE" }
}

Run-HostIntegrationTest 'test_app_integration' 'host_test_app' @($hostMocks)
Run-HostIntegrationTest 'test_bank_driver' 'host_test_driver' @()

Write-Host ''
Write-Host 'Application logic tests: PASS'
Write-Host 'Application integration tests: PASS'
Write-Host 'Bank driver integration tests: PASS'
foreach ($image in $builtElfs.Keys) {
    Write-Host "Built: $(Join-Path $build "$image.hex")"
}
