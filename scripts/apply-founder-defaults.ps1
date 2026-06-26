# Apply founder defaults (PowerShell wrapper).
param([switch]$Force)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$args = @()
if ($Force) { $args += "--force" }
& bash scripts/apply-founder-defaults.sh @args
exit $LASTEXITCODE
