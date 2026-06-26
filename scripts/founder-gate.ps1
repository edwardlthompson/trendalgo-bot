# Founder gate CLI wrapper (PowerShell).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$py = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
& $py scripts/founder_gate.py @Args
exit $LASTEXITCODE
