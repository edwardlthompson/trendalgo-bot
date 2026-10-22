# Launch the TrendAlgo device GUI with no console window.
# Closing a console must never kill the app - use this (or Start Menu / MSI),
# never `uv run python -m trendalgo.device` for normal GUI runs.
#
# Usage (repo root):
#   .\scripts\packaging\launch-device.ps1              # source-first (pythonw) when .venv exists
#   .\scripts\packaging\launch-device.ps1 -Source      # same as default when venv present
#   .\scripts\packaging\launch-device.ps1 -Frozen      # packaging / MSI verification
#   .\scripts\packaging\launch-device.ps1 -KeepConsole # testing only
#   .\scripts\packaging\launch-device.ps1 -DataDir "$env:USERPROFILE\.trendalgo\device"
#
# Preference order is mirrored in scripts/lib/device_launch_prefer.py (keep in sync).
param(
    [string]$DataDir = "",
    [switch]$KeepConsole,
    [switch]$Source,
    [switch]$Frozen
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

if ($Source -and $Frozen) {
    throw "Use only one of -Source or -Frozen."
}

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

# Path vars must not collide with -[Ss]witch switches (PowerShell is case-insensitive).
$frozenExe = Join-Path $Root "dist\windows-device\TrendAlgoDevice\TrendAlgoDevice.exe"
$localApp = Join-Path $env:LOCALAPPDATA "Programs\TrendAlgo\app\TrendAlgoDevice.exe"
$msiLike = Join-Path ${env:ProgramFiles(x86)} "TrendAlgo\TrendAlgoDevice.exe"
if (-not (Test-Path $msiLike)) {
    $msiLike = Join-Path $env:ProgramFiles "TrendAlgo\TrendAlgoDevice.exe"
}
$pythonw = Join-Path $Root ".venv\Scripts\pythonw.exe"
$python = Join-Path $Root ".venv\Scripts\python.exe"

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

function Start-FrozenChain {
    if (Test-Path $frozenExe) {
        Start-NoConsole $frozenExe
        Write-Host "Launched frozen device (no console): $frozenExe"
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

if ($KeepConsole) {
    if (-not (Test-Path $python)) {
        throw "Missing $python - run uv sync --extra device first."
    }
    Start-NoConsole $python "-m trendalgo.device"
    Write-Host "Launched with console (testing): $python"
    Write-Host "DATA_DIR=$DataDir"
    exit 0
}

if ($Frozen) {
    Start-FrozenChain
    if (Test-Path $pythonw) {
        Start-NoConsole $pythonw "-m trendalgo.device"
        Write-Host "No frozen build found; fell back to pythonw: $pythonw"
        Write-Host "DATA_DIR=$DataDir"
        exit 0
    }
    throw "Missing frozen/installed device. Run build-windows-desktop.ps1 -Device, or omit -Frozen."
}

# Source-first default (and -Source): live src/ via pythonw — no PyInstaller rebuild.
if (Test-Path $pythonw) {
    Start-NoConsole $pythonw "-m trendalgo.device"
    Write-Host "Launched pythonw device (no console): $pythonw"
    Write-Host "DATA_DIR=$DataDir"
    exit 0
}

# No venv: fall back to any packaged binary.
Start-FrozenChain
throw "Missing $pythonw - run uv sync --extra device, or build the frozen app (-Frozen)."
