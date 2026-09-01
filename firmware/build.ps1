$ErrorActionPreference = 'Stop'

$avrRoot = 'C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\Tools\ARDUINO\hardware\tools\avr'
$gcc = Join-Path $avrRoot 'bin\avr-gcc.exe'
$objcopy = Join-Path $avrRoot 'bin\avr-objcopy.exe'
$size = Join-Path $avrRoot 'bin\avr-size.exe'
$include = Join-Path $PSScriptRoot 'include'
$build = Join-Path $PSScriptRoot 'build'

New-Item -ItemType Directory -Path $build -Force | Out-Null

# Remove only generated firmware products, never source files.
Get-ChildItem -LiteralPath $build -File | Where-Object {
    $_.Extension -in @('.o', '.elf', '.hex')
} | Remove-Item -Force

$commonFlags = @(
    '-std=c11', '-Os', '-Wall', '-Wextra', '-Werror', '-mmcu=atmega32',
    '-DF_CPU=8000000UL', "-I$include", '-ffunction-sections', '-fdata-sections'
)

$commonSources = [ordered]@{
    'mcal_gpio'       = 'mcal\gpio.c'
    'mcal_spi'        = 'mcal\spi.c'
    'mcal_board'      = 'mcal\board.c'
    'hal_lcd'         = 'hal\lcd.c'
    'hal_alarm'       = 'hal\alarm_output.c'
    'app_logic'       = 'app\app_logic.c'
    'app_main'        = 'app\main.c'
}

function Compile-Source([string]$objectName, [string]$relativeSource) {
    $sourcePath = Join-Path $PSScriptRoot (Join-Path 'src' $relativeSource)
    $objectPath = Join-Path $build "$objectName.o"
    & $gcc @commonFlags '-c' $sourcePath '-o' $objectPath
    if ($LASTEXITCODE -ne 0) { throw "Compilation failed: $relativeSource" }
    return $objectPath
}

$commonObjects = foreach ($entry in $commonSources.GetEnumerator()) {
    Compile-Source $entry.Key $entry.Value
}
$max31856Object = Compile-Source 'hal_temperature_max31856' 'hal\temperature_max31856.c'
$max6675Object = Compile-Source 'hal_temperature_max6675' 'hal\temperature_max6675.c'

$max31856Elf = Join-Path $build 'thermocouple_meter_max31856.elf'
$max31856Hex = Join-Path $build 'thermocouple_meter_max31856.hex'
$max6675Elf = Join-Path $build 'thermocouple_meter_max6675.elf'
$max6675Hex = Join-Path $build 'thermocouple_meter_max6675.hex'

& $gcc '-mmcu=atmega32' '-Wl,--gc-sections' @commonObjects $max31856Object '-o' $max31856Elf
if ($LASTEXITCODE -ne 0) { throw 'MAX31856 linking failed.' }
& $objcopy '-O' 'ihex' '-R' '.eeprom' $max31856Elf $max31856Hex
if ($LASTEXITCODE -ne 0) { throw 'MAX31856 HEX generation failed.' }

& $gcc '-mmcu=atmega32' '-Wl,--gc-sections' @commonObjects $max6675Object '-o' $max6675Elf
if ($LASTEXITCODE -ne 0) { throw 'MAX6675 linking failed.' }
& $objcopy '-O' 'ihex' '-R' '.eeprom' $max6675Elf $max6675Hex
if ($LASTEXITCODE -ne 0) { throw 'MAX6675 HEX generation failed.' }

Write-Host 'MAX31856 image:'
& $size '-C' '--mcu=atmega32' $max31856Elf
if ($LASTEXITCODE -ne 0) { throw 'MAX31856 size report failed.' }
Write-Host 'MAX6675 image:'
& $size '-C' '--mcu=atmega32' $max6675Elf
if ($LASTEXITCODE -ne 0) { throw 'MAX6675 size report failed.' }

$hostBuild = Join-Path $build 'host_tests'
$testExe = Join-Path $hostBuild 'test_app_logic.exe'
$testSource = Join-Path $PSScriptRoot 'tests\test_app_logic.c'
$appLogicSource = Join-Path $PSScriptRoot 'src\app\app_logic.c'
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
$compileCommand = "call `"$vsDevCmd`" -arch=x64 -no_logo && cl /nologo /std:c11 /W4 /WX /I`"$include`" `"$testSource`" `"$appLogicSource`" /Fe:`"$testExe`" /Fo:$hostBuild\"
& $env:ComSpec /d /s /c $compileCommand
if ($LASTEXITCODE -ne 0) { throw 'Application logic test compilation failed.' }
& $testExe
if ($LASTEXITCODE -ne 0) { throw "Application logic tests failed: $LASTEXITCODE" }
Write-Host 'Application logic tests: PASS'

Write-Host "Built: $max31856Hex"
Write-Host "Built: $max6675Hex"
