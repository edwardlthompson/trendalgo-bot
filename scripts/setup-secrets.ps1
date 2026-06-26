# setup-secrets.ps1 wrapper
param()
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (Get-Command bash -ErrorAction SilentlyContinue) {
  & bash scripts/setup-secrets.sh
  exit $LASTEXITCODE
}
Write-Host "FAIL: bash required for setup-secrets.sh"
exit 1
