# setup-trendalgo-repo.ps1 wrapper
param([string]$Repo = "edwardlthompson/trendalgo-bot")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
& bash scripts/setup-trendalgo-repo.sh $Repo
exit $LASTEXITCODE
