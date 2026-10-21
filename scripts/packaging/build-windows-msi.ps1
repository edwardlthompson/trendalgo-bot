# Build TrendAlgo device MSI + Burn setup.exe for GitHub Release assets.
# Prerequisites: WiX 5.x (`dotnet tool install -g wix --version 5.0.2`),
#   device onedir already built (or pass -BuildDevice).
#   Extension: WixToolset.BootstrapperApplications.wixext (setup.exe).
#   Do not use WiX 7+ here (OSMF EULA); WiX 4 lacks Files harvest.
#
# Usage (from repo root):
#   .\scripts\packaging\build-windows-msi.ps1
#   .\scripts\packaging\build-windows-msi.ps1 -BuildDevice
#   .\scripts\packaging\build-windows-msi.ps1 -MsiOnly
#   .\scripts\packaging\build-windows-msi.ps1 -SetupOnly
param(
    [switch]$BuildDevice,
    [switch]$MsiOnly,
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

if ($MsiOnly -and $SetupOnly) {
    throw "Use only one of -MsiOnly / -SetupOnly."
}

$ver = (Get-Content (Join-Path $Root ".template-version") -Raw).Trim()
if ($ver -notmatch '^\d+\.\d+\.\d+') {
    throw "Invalid .template-version: $ver"
}
# WiX ProductVersion needs four parts for some tools; MSI uses major.minor.build.
$productVersion = "$ver.0"

$deviceDir = Join-Path $Root "dist\windows-device\TrendAlgoDevice"
$exe = Join-Path $deviceDir "TrendAlgoDevice.exe"
$msiOutDir = Join-Path $Root "dist\windows-msi"
$wixDir = Join-Path $PSScriptRoot "wix"
$msiPath = Join-Path $msiOutDir "TrendAlgo-$ver-x64.msi"
$setupPath = Join-Path $msiOutDir "TrendAlgo-$ver-x64-setup.exe"

if ($BuildDevice -or -not (Test-Path $exe)) {
    Write-Host "Building frozen device app..."
    & (Join-Path $PSScriptRoot "build-windows-desktop.ps1") -Device
    if ($LASTEXITCODE -ne 0) { throw "Device build failed." }
}

if (-not (Test-Path $exe)) {
    throw "Missing $exe. Run build-windows-desktop.ps1 -Device first."
}

Write-Host "Self-test: $exe --selftest"
$ErrorActionPreference = "Continue"
& $exe --selftest
$selftestExit = $LASTEXITCODE
$ErrorActionPreference = "Stop"
# Windowed pyinstaller sometimes leaves LASTEXITCODE unset after a clean run.
if ($null -ne $selftestExit -and $selftestExit -ne 0) {
    throw "Frozen device self-test failed (exit $selftestExit)."
}

Get-Command wix -ErrorAction Stop | Out-Null
New-Item -ItemType Directory -Force -Path $msiOutDir | Out-Null

# WiX 5.x (not 4.x — no Files harvest; not 7.x — OSMF EULA).
$wixVer = (wix --version 2>$null | Select-Object -First 1)
if ($wixVer -notmatch '^5\.') {
    Write-Warning "Expected WiX 5.x (got '$wixVer'). Install: dotnet tool install -g wix --version 5.0.2"
}
# WiX 5 renamed Bal → BootstrapperApplications
wix extension add -g WixToolset.BootstrapperApplications.wixext/5.0.2 2>$null | Out-Null

if (-not $SetupOnly) {
    Write-Host "Building MSI -> $msiPath"
    $msiArgs = @(
        "build",
        (Join-Path $wixDir "TrendAlgoDevice.wxs"),
        "-arch", "x64",
        "-d", "ProductVersion=$productVersion",
        "-bindpath", "Payload=$deviceDir",
        "-out", $msiPath,
        "-pdbtype", "none"
    )
    & wix @msiArgs
    if ($LASTEXITCODE -ne 0) { throw "wix build MSI failed." }
    if (-not (Test-Path $msiPath)) { throw "MSI not produced: $msiPath" }
    Write-Host "MSI ready: $msiPath ($([math]::Round((Get-Item $msiPath).Length / 1MB, 1)) MB)"
}

if (-not $MsiOnly) {
    if (-not (Test-Path $msiPath)) {
        throw "Missing MSI for Burn bundle: $msiPath (run without -SetupOnly first)."
    }
    Write-Host "Building setup.exe -> $setupPath"
    $bundleArgs = @(
        "build",
        (Join-Path $wixDir "TrendAlgoDevice.bundle.wxs"),
        "-ext", "WixToolset.BootstrapperApplications.wixext",
        "-arch", "x64",
        "-d", "ProductVersion=$productVersion",
        "-d", "MsiPath=$msiPath",
        "-out", $setupPath,
        "-pdbtype", "none"
    )
    & wix @bundleArgs
    if ($LASTEXITCODE -ne 0) { throw "wix build setup.exe failed." }
    if (-not (Test-Path $setupPath)) { throw "setup.exe not produced: $setupPath" }
    Write-Host "Setup ready: $setupPath ($([math]::Round((Get-Item $setupPath).Length / 1MB, 1)) MB)"
}

Write-Host "Release assets:"
Get-ChildItem $msiOutDir -Filter "TrendAlgo-$ver-x64*" | ForEach-Object { "  $($_.Name)  $($_.Length) bytes" }
exit 0
