# Install / refresh TrendAlgo device shortcuts (Start Menu, Desktop, taskbar pin).
# Replaces the retired pywebview "TrendAlgo Desktop" launcher with TrendAlgoDevice.
#
# Usage (from repo root):
#   .\scripts\packaging\install-windows-device.ps1
#   .\scripts\packaging\install-windows-device.ps1 -SkipBuild
#   .\scripts\packaging\install-windows-device.ps1 -DataDir "D:\trendalgo-data"
param(
    [switch]$SkipBuild,
    [string]$DataDir = ""
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

# Drop any running windowed app so the profile lock and old binary do not stick around.
Get-Process -Name TrendAlgoDevice -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$deviceDir = Join-Path $Root "dist\windows-device\TrendAlgoDevice"
$exe = Join-Path $deviceDir "TrendAlgoDevice.exe"

if (-not $SkipBuild) {
    Write-Host "Building frozen device app..."
    & (Join-Path $PSScriptRoot "build-windows-desktop.ps1") -Device
    if ($LASTEXITCODE -ne 0) { throw "Device build failed." }
}

if (-not (Test-Path $exe)) {
    throw "Missing $exe. Run without -SkipBuild, or build first."
}

if (-not $DataDir) {
    $DataDir = Join-Path $Root "data"
}
$DataDir = (Resolve-Path $DataDir).Path

$installDir = Join-Path $env:LOCALAPPDATA "Programs\TrendAlgo"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

# Junction so upgrades that rebuild dist\ are picked up without re-copying the tree.
$appLink = Join-Path $installDir "app"
if (Test-Path $appLink) {
    cmd /c rmdir "$appLink" 2>$null | Out-Null
    if (Test-Path $appLink) { Remove-Item -LiteralPath $appLink -Recurse -Force }
}
cmd /c mklink /J "$appLink" "$deviceDir" | Out-Null
if (-not (Test-Path (Join-Path $appLink "TrendAlgoDevice.exe"))) {
    # Fallback: copy if junction fails (e.g. non-admin + policy).
    Copy-Item -Path (Join-Path $deviceDir "*") -Destination $installDir -Recurse -Force
    $launchExe = Join-Path $installDir "TrendAlgoDevice.exe"
} else {
    $launchExe = Join-Path $appLink "TrendAlgoDevice.exe"
}

$icon = Join-Path $Root "branding\assets\app-icon.ico"
if (-not (Test-Path $icon)) {
    $icon = Join-Path $installDir "app-icon.ico"
}
if (Test-Path (Join-Path $Root "branding\assets\app-icon.ico")) {
    Copy-Item (Join-Path $Root "branding\assets\app-icon.ico") (Join-Path $installDir "app-icon.ico") -Force
    $icon = Join-Path $installDir "app-icon.ico"
}

$coinIcons = Join-Path $Root "branding\assets\coins\from-retired-web-backup"
if (-not (Test-Path $coinIcons)) {
    $coinIcons = Join-Path $Root "branding\assets\coins"
}

# CMD kept for scripts; Start Menu / Desktop use VBS so no console flashes.
$launcherCmd = Join-Path $installDir "launch-device.cmd"
@(
    "@echo off"
    "set `"TRENDALGO_DATA_DIR=$DataDir`""
    "set `"TRENDALGO_DEVICE_DIR=$DataDir`""
    "set `"TRENDALGO_ROOT=$Root`""
    "set `"TRENDALGO_COIN_ICONS=$coinIcons`""
    "start `"`" `"$launchExe`""
) | Set-Content -Path $launcherCmd -Encoding ASCII

$launcherVbs = Join-Path $installDir "launch-device.vbs"
@"
' Silent launcher: sets env and starts the windowed TrendAlgoDevice.exe (no console).
Option Explicit
Dim sh
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "$installDir"
sh.Environment("PROCESS")("TRENDALGO_DATA_DIR") = "$DataDir"
sh.Environment("PROCESS")("TRENDALGO_DEVICE_DIR") = "$DataDir"
sh.Environment("PROCESS")("TRENDALGO_ROOT") = "$Root"
sh.Environment("PROCESS")("TRENDALGO_COIN_ICONS") = "$coinIcons"
sh.Run """$launchExe""", 1, False
"@ | Set-Content -Path $launcherVbs -Encoding ASCII

# Redirect legacy TrendAlgo.vbs / .pyw leftovers to the frozen windowed exe.
$legacyVbs = Join-Path $installDir "TrendAlgo.vbs"
Copy-Item -LiteralPath $launcherVbs -Destination $legacyVbs -Force

(Set-Content -Path (Join-Path $installDir "repo.root") -Value $Root -Encoding ASCII)

function Set-TrendAlgoShortcut([string]$Path, [string]$Name) {
    $dir = Split-Path $Path -Parent
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $w = New-Object -ComObject WScript.Shell
    $s = $w.CreateShortcut($Path)
    $s.TargetPath = $launcherVbs
    $s.WorkingDirectory = $installDir
    $s.WindowStyle = 1
    $s.Description = "TrendAlgo Bot (device)"
    if (Test-Path $icon) { $s.IconLocation = "$icon,0" }
    $s.Save()
    Write-Host "Shortcut: $Path"
}

$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\TrendAlgo\TrendAlgo.lnk"
$desktop = Join-Path $env:USERPROFILE "Desktop\TrendAlgo.lnk"
$taskbar = Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\TrendAlgo Desktop.lnk"

Set-TrendAlgoShortcut $startMenu "TrendAlgo"
Set-TrendAlgoShortcut $desktop "TrendAlgo"
if (Test-Path (Split-Path $taskbar -Parent)) {
    Set-TrendAlgoShortcut $taskbar "TrendAlgo Desktop"
}

Write-Host ""
Write-Host "Installed device launcher (no console):"
Write-Host "  $launcherVbs"
Write-Host "  DATA_DIR=$DataDir"
Write-Host "Start Menu / Desktop shortcuts updated. If the taskbar still opens an old pin, unpin and re-pin from Start Menu."

Write-Host "Launching TrendAlgoDevice..."
Start-Process -FilePath "wscript.exe" -ArgumentList "`"$launcherVbs`""
