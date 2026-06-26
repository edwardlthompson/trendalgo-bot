# check-legal-compliance.ps1 wrapper
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
& bash scripts/check-legal-compliance.sh
exit $LASTEXITCODE
