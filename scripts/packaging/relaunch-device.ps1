# Stop any running device GUI, clear pending_crash, launch source-first (pythonw).
# Day-to-day UI loop after editing src/ — do not rebuild PyInstaller for this.
#
# Usage (repo root):
#   .\scripts\packaging\relaunch-device.ps1
#   .\scripts\packaging\relaunch-device.ps1 -Frozen
#   .\scripts\packaging\relaunch-device.ps1 -DataDir "$env:USERPROFILE\.trendalgo\device"
param(
    [string]$DataDir = "",
    [switch]$Frozen,
    [switch]$KeepConsole
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

Get-Process -Name TrendAlgoDevice -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*trendalgo.device*" } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Start-Sleep -Seconds 1

$crash = Join-Path $env:USERPROFILE ".trendalgo\device\pending_crash.json"
Remove-Item -LiteralPath $crash -Force -ErrorAction SilentlyContinue

$launch = Join-Path $PSScriptRoot "launch-device.ps1"
# Hashtable splat (array splat would bind "-DataDir" as the DataDir value).
$launchArgs = @{}
if ($DataDir) { $launchArgs["DataDir"] = $DataDir }
if ($Frozen) { $launchArgs["Frozen"] = $true }
if ($KeepConsole) { $launchArgs["KeepConsole"] = $true }
& $launch @launchArgs
