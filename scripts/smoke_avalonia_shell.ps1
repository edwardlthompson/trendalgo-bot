#Requires -Version 5.1
# Build + launch Avalonia shell, assert process stays up, run Python contract smoke.
param(
  [int]$SettleSeconds = 5
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

Write-Host "== contract smoke =="
uv run python scripts/smoke_avalonia_vm.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== build shell =="
dotnet build shell/TrendAlgo.Shell.sln -c Release -v q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Get-Process -Name TrendAlgo.Shell -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$err = Join-Path $env:TEMP "avalonia-smoke-err.txt"
$out = Join-Path $env:TEMP "avalonia-smoke-out.txt"
Remove-Item $err, $out -ErrorAction SilentlyContinue

Write-Host "== launch shell =="
$p = Start-Process -FilePath "dotnet" `
  -ArgumentList @("run", "--project", "shell\TrendAlgo.Shell", "-c", "Release", "--no-build") `
  -WorkingDirectory $root -PassThru `
  -RedirectStandardError $err -RedirectStandardOutput $out

Start-Sleep -Seconds $SettleSeconds
if ($p.HasExited) {
  Write-Host "FAIL: shell exited $($p.ExitCode)"
  Get-Content $err -ErrorAction SilentlyContinue | Select-Object -First 40
  exit 1
}

$proc = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
$title = (Get-Process -Name TrendAlgo.Shell -ErrorAction SilentlyContinue | Select-Object -First 1).MainWindowTitle
Write-Host "OK shell alive pid=$($p.Id) title=$title"

# Soft UI smoke: invoke reload via a second short-lived ViewModel-equivalent — already covered in Python.
# Keep GUI up for human; do not kill.
Write-Host "SMOKE PASS (shell left running for manual click-through)"
exit 0
