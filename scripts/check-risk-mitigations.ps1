# check-risk-mitigations.ps1 wrapper
param([switch]$Strict, [int]$Sprint = -1, [switch]$Ongoing, [switch]$All)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$args = @("check")
if ($Strict) { $args += "--strict" }
if ($Sprint -ge 0) { $args += "--sprint"; $args += "$Sprint" }
if ($Ongoing) { $args += "--ongoing" }
if ($All) { $args += "--all" }
& python3 scripts/check_risk_mitigations.py @args
exit $LASTEXITCODE
