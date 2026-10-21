# Launch the TrendAlgo device GUI with no console window.
# Closing a console must never kill the app - use this (or Start Menu / MSI),
# never `uv run python -m trendalgo.device` for normal GUI runs.
#
# Usage (repo root):
#   .\scripts\packaging\launch-device.ps1
#   .\scripts\packaging\launch-device.ps1 -DataDir "$env:USERPROFILE\.trendalgo\device"
#   .\scripts\packaging\launch-device.ps1 -KeepConsole   # testing only
#   .\scripts\packaging\launch-device.ps1 -Source        # repo .venv pythonw (not frozen)
param(
    [string]$DataDir = "",
    [switch]$KeepConsole,
    [switch]$Source
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

if (-not $DataDir) {
    $profileDir = Join-Path $env:USERPROFILE ".trendalgo\device"
    if (Test-Path $profileDir) {
        $DataDir = $profileDir
    } else {
        $DataDir = (Resolve-Path (Join-Path $Root "data")).Path
    }
} else {
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    $DataDir = (Resolve-Path $DataDir).Path
}

$env:TRENDALGO_DATA_DIR = $DataDir
$env:TRENDALGO_DEVICE_DIR = $DataDir
if ($KeepConsole) {
    $env:TRENDALGO_KEEP_CONSOLE = "1"
} else {
    Remove-Item Env:TRENDALGO_KEEP_CONSOLE -ErrorAction SilentlyContinue
}

$frozen = Join-Path $Root "dist\windows-device\TrendAlgoDevice\TrendAlgoDevice.exe"
$localApp = Join-Path $env:LOCALAPPDATA "Programs\TrendAlgo\app\TrendAlgoDevice.exe"
$msiLike = Join-Path ${env:ProgramFiles(x86)} "TrendAlgo\TrendAlgoDevice.exe"
if (-not (Test-Path $msiLike)) {
    $msiLike = Join-Path $env:ProgramFiles "TrendAlgo\TrendAlgoDevice.exe"
}

function Start-NoConsole([string]$File, [string]$Arguments = "") {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $File
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $Root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = -not $KeepConsole
    if ($KeepConsole) {
        $psi.UseShellExecute = $true
    }
    [void][System.Diagnostics.Process]::Start($psi)
}

if (-not $Source -and -not $KeepConsole) {
    if (Test-Path $frozen) {
        Start-NoConsole $frozen
        Write-Host "Launched frozen device (no console): $frozen"
        exit 0
    }
    if (Test-Path $localApp) {
        Start-NoConsole $localApp
        Write-Host "Launched installed device (no console): $localApp"
        exit 0
    }
    if (Test-Path $msiLike) {
        Start-NoConsole $msiLike
        Write-Host "Launched MSI device (no console): $msiLike"
        exit 0
    }
}

$pythonw = Join-Path $Root ".venv\Scripts\pythonw.exe"
$python = Join-Path $Root ".venv\Scripts\python.exe"
if ($KeepConsole) {
    if (-not (Test-Path $python)) {
        throw "Missing $python - run uv sync --extra device first."
    }
    Start-NoConsole $python "-m trendalgo.device"
    Write-Host "Launched with console (testing): $python"
    exit 0
}
if (-not (Test-Path $pythonw)) {
    throw "Missing $pythonw - run uv sync --extra device, or build the frozen app."
}
Start-NoConsole $pythonw "-m trendalgo.device"
Write-Host "Launched pythonw device (no console): $pythonw"
Write-Host "DATA_DIR=$DataDir"
