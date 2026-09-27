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

# Warning classes that are tolerated. endpoint_off_grid is the whole of I-002:
# 192 of them, every one because the sheet has labels instead of wires, and it
# is tracked. Any other warning class fails - see the note below.
$script:ErcToleratedWarnings = @('endpoint_off_grid')

function Assert-ErcReport {
    param([Parameter(Mandatory)][string]$Path)
    $report = Get-Content -LiteralPath $Path -Raw
    $counts = [regex]::Match($report, 'ERC messages:\s*(\d+)\s+Errors\s+(\d+)\s+Warnings\s+(\d+)')
    if (-not $counts.Success) { throw "Unrecognized ERC report: $Path" }
    Write-Output "ERC: $($counts.Groups[2].Value) errors, $($counts.Groups[3].Value) warnings ($Path)"
    if ([int]$counts.Groups[2].Value -ne 0) { throw "ERC errors: $Path" }

    # Errors alone are not enough. On 2026-09-15 a stale SPARE_PC2 label sat on
    # U1 pin 24 beside the new RUN_PERMIT_SENSE one; ERC called it
    # [multiple_net_names] - a WARNING - so this gate was green while a safety
    # read-back net had two names and KiCad chose which one reached the
    # netlist. A gate that only counts errors would have shipped that.
    $classes = [regex]::Matches($report, '\[([a-z_]+)\]') |
               ForEach-Object { $_.Groups[1].Value } |
               Sort-Object -Unique
    $unexpected = $classes | Where-Object { $_ -notin $script:ErcToleratedWarnings }
    if ($unexpected) {
        $bad = $unexpected -join ', '
        $ok = $script:ErcToleratedWarnings -join ', '
        throw "ERC warning classes that are not tolerated: $bad ($Path). Tolerated: $ok. Either fix the schematic, or if the class is genuinely benign here add it to `$script:ErcToleratedWarnings with the reason."
    }
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
