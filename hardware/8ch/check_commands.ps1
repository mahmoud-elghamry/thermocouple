# Shared native-command and report gates. Warnings are reported, errors fail.
function Invoke-CheckedNative {
    param([Parameter(Mandatory)][string]$Command,
          [string[]]$Arguments = @(),
          [int[]]$AllowedExitCodes = @(0))
    & $Command @Arguments
    if ($LASTEXITCODE -notin $AllowedExitCodes) {
        throw "$Command failed (exit $LASTEXITCODE); stopping before the next stage."
    }
}

function Assert-ErcReport {
    param([Parameter(Mandatory)][string]$Path)
    $report = Get-Content -LiteralPath $Path -Raw
    $counts = [regex]::Match($report, 'ERC messages:\s*(\d+)\s+Errors\s+(\d+)\s+Warnings\s+(\d+)')
    if (-not $counts.Success) { throw "Unrecognized ERC report: $Path" }
    Write-Output "ERC: $($counts.Groups[2].Value) errors, $($counts.Groups[3].Value) warnings ($Path)"
    if ([int]$counts.Groups[2].Value -ne 0) { throw "ERC errors: $Path" }
}

function Assert-DrcReport {
    param([Parameter(Mandatory)][string]$Path)
    $report = Get-Content -LiteralPath $Path -Raw
    $violations = [regex]::Match($report, 'Found (\d+) DRC violations')
    $unconnected = [regex]::Match($report, 'Found (\d+) unconnected pads')
    $parity = [regex]::Match($report, 'Found (\d+) Footprint errors')
    if (-not ($violations.Success -and $unconnected.Success -and $parity.Success)) {
        throw "Unrecognized or incomplete DRC report: $Path"
    }
    $errors = [regex]::Matches($report, '(?im);\s*error\s*$').Count
    $warnings = [regex]::Matches($report, '(?im);\s*warning\s*$').Count
    if ($errors + $warnings -lt [int]$violations.Groups[1].Value) {
        throw "Unrecognized DRC severity entries: $Path"
    }
    Write-Output "DRC: $errors errors, $warnings warnings, $($unconnected.Groups[1].Value) unconnected, $($parity.Groups[1].Value) parity ($Path)"
    if ($errors -ne 0 -or [int]$unconnected.Groups[1].Value -ne 0 -or [int]$parity.Groups[1].Value -ne 0) {
        throw "DRC errors or connectivity/parity failure: $Path"
    }
}
