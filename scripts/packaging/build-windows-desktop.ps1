# TrendAlgo - build the frozen Windows device app (PySide6, ADR-0016, row 17).
# The pywebview desktop shell and the PWA build were retired in row 23 (p7-retire-pwa, 2026-10-10).
# Usage (from repo root):
#   .\scripts\packaging\build-windows-desktop.ps1 -Device   # frozen PySide6 device app under dist\windows-device\
param(
    [switch]$Device
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "TrendAlgo Device Build"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

# Device app only. No build uses the desktop extra (pywebview) any more.
$syncExtras = @("--extra", "device", "--extra", "dev")

# Windows PowerShell turns native stderr into a terminating error under Stop, so the probe
# runs with Continue and reads $LASTEXITCODE.
function Invoke-PyInstallerProbe {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    uv run --no-sync python -c "import PyInstaller" 2>$null
    $script:HasPyInstaller = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $previousPreference
}

if (-not $Device) {
    Write-Host "The pywebview desktop shell and the PWA build are retired (row 23). Run with -Device."
    exit 1
}

# Frozen device app (ADR-0016, row 17). One folder; --windowed so Start Menu / Desktop launch
# has no console. --selftest still AllocConsole() for the build report.
Write-Host "Syncing Python deps (device, dev extras)..."
uv sync @syncExtras
Invoke-PyInstallerProbe
if (-not $script:HasPyInstaller) {
    uv pip install pyinstaller
}
$deviceOut = Join-Path $Root "dist\windows-device"
New-Item -ItemType Directory -Force -Path $deviceOut | Out-Null
uv run --no-sync pyinstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name TrendAlgoDevice `
    --distpath $deviceOut `
    --workpath (Join-Path $deviceOut "build") `
    --specpath (Join-Path $deviceOut "spec") `
    --paths (Join-Path $Root "src") `
    --collect-submodules talib `
    --collect-all pandas_ta_classic `
    --collect-submodules PySide6.QtCharts `
    --icon (Join-Path $Root "branding\assets\app-icon.ico") `
    --add-data ((Join-Path $Root "branding\assets\app-icon-192.png") + ";branding/assets") `
    --add-data ((Join-Path $Root "branding\assets\splash-1280x720.png") + ";branding/assets") `
    --add-data ((Join-Path $Root "src\trendalgo\device\data\ta-glossary.json") + ";trendalgo/device/data") `
    (Join-Path $Root "src\trendalgo\device\__main__.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for the device app." }
$exe = Join-Path $deviceOut "TrendAlgoDevice\TrendAlgoDevice.exe"
& $exe --selftest
if ($LASTEXITCODE -ne 0) { throw "Frozen device self-test failed. Read the FAIL lines above." }
Write-Host "Device app ready: $exe"
exit 0
