# check-human-backlog.ps1 wrapper
param([int]$Sprint = 0, [switch]$Strict)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$args = @("preflight-sprint", "--sprint", "$Sprint")
if ($Strict) { $args += "--strict" }
& python3 scripts/founder_gate.py @args
exit $LASTEXITCODE
