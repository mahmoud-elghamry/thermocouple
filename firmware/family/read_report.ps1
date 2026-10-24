# Capture the service-mode report (08 section 2) from the RS-485 port into a file.
# Usage: read_report.ps1 -Board 01 [-Port COM5] [-Seconds 600]
# The board prints plain text at 9600 8N1 while SET was held at power-up; the capture stops after the END line.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Board,[string]$Port,[int]$Seconds=600)
$ErrorActionPreference='Stop'
$ports=[System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object -Unique
if(-not $Port) {
    if(-not $ports) { throw 'No serial port: plug in the USB-RS485 adapter and check Device Manager' }
    if(@($ports).Count -ne 1) { throw "Several serial ports ($($ports -join ', ')): pass -Port COMn" }
    $Port=$ports[0]
}
$dir=Join-Path $PSScriptRoot '../../production/bench'
New-Item -ItemType Directory -Force $dir | Out-Null
$file=Join-Path $dir ("report-board{0}-{1:yyyyMMdd-HHmmss}.txt" -f $Board,(Get-Date))
$sp=New-Object System.IO.Ports.SerialPort $Port,9600,'None',8,'One'
$sp.NewLine="`r`n"; $sp.ReadTimeout=1000
$sp.Open()
Write-Host "Listening on $Port at 9600; hold SET while powering the board. Saving to $file"
$deadline=(Get-Date).AddSeconds($Seconds)
try {
    while((Get-Date) -lt $deadline) {
        try { $line=$sp.ReadLine() } catch [System.TimeoutException] { continue }
        $line=$line.TrimEnd()
        if(-not $line) { continue }
        Write-Host $line
        Add-Content -LiteralPath $file -Value $line
        if($line -match '^END ') { break }
    }
} finally { $sp.Close() }
if(Test-Path -LiteralPath $file) { Write-Host "Saved: $file" } else { Write-Host 'No report received: check A/B, the COM port and that SET was held at power-up.' }
