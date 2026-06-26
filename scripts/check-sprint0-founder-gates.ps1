# check-sprint0-founder-gates.ps1 wrapper
param([switch]$Strict)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$args = @()
if ($Strict) { $args += "--strict" }
& python3 scripts/check_risk_mitigations.py --sprint 0 @args
& python3 scripts/founder_gate.py preflight-sprint --sprint 0 @args
if (Get-Command bash -ErrorAction SilentlyContinue) {
  & bash scripts/check-legal-compliance.sh
} else {
  if (-not (Test-Path docs/adr/0009-ai-recommended-strategies.md)) { exit 1 }
}
exit $LASTEXITCODE
