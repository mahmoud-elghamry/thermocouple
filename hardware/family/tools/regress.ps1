# Run by the orchestrator outside the implementer's sandbox. No routing runs.
param([string]$Python = 'C:\Users\malgh\AppData\Local\Programs\Python\Python310\python.exe')
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:KICAD_CLI = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
$env:KICAD_PYTHON = 'C:\Program Files\KiCad\10.0\bin\python.exe'
# Child processes inherit this setting: crashes must not open a desktop dialog.
if ($env:OS -eq 'Windows_NT') {
    Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public class ThermoErrorMode { [DllImport("kernel32.dll")] public static extern uint SetErrorMode(uint mode); }'
    [void][ThermoErrorMode]::SetErrorMode(0x8003)
}
try {
    & $Python -B "$PSScriptRoot\regress.py"
    $result = $LASTEXITCODE
} catch {
    Write-Error $_
    exit 1
}
exit $result
