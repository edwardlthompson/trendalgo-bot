# Install and configure WSL + Ubuntu for TrendAlgo bash gates.
# Usage (Admin PowerShell): .\scripts\setup-wsl.ps1
# Optional: .\scripts\setup-wsl.ps1 -Distro Ubuntu-24.04 -PreferWsl2
param(
  [string]$Distro = "Ubuntu-24.04",
  [switch]$PreferWsl2,
  [switch]$SkipLinuxDeps
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Test-Admin {
  $id = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
  return $id.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-WslHypervisor {
  $out = wsl --install -d $Distro --no-launch --dry-run 2>&1 | Out-String
  if ($out -match "HCS_E_HYPERV_NOT_INSTALLED|virtualization is not enabled") { return $false }
  # dry-run may not exist on all builds; probe with a lightweight check instead
  $status = wsl --status 2>&1 | Out-String
  return $true
}

function Get-InstalledDistro {
  $list = wsl --list --quiet 2>&1 | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -notmatch "^\s*$" }
  return ($list -contains $Distro)
}

Write-Host "=== TrendAlgo WSL setup ===" -ForegroundColor Cyan

if (-not (Test-Admin)) {
  Write-Warning "Not running as Administrator. Re-run PowerShell as Admin for feature enable + distro install."
  Write-Host "  Right-click PowerShell -> Run as administrator"
  Write-Host "  cd $Root"
  Write-Host "  .\scripts\setup-wsl.ps1"
}

# Ensure Windows optional components (idempotent; may require reboot)
foreach ($feature in @("VirtualMachinePlatform", "Microsoft-Windows-Subsystem-Linux")) {
  $state = (Get-WindowsOptionalFeature -Online -FeatureName $feature -ErrorAction SilentlyContinue).State
  if ($state -ne "Enabled") {
    Write-Host "Enabling Windows feature: $feature"
    Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart | Out-Null
    $script:RebootNeeded = $true
  }
}

Write-Host "Updating WSL kernel/components..."
wsl --update 2>&1 | Out-Host

$installed = Get-InstalledDistro
if (-not $installed) {
  $useWsl2 = $PreferWsl2.IsPresent
  if ($useWsl2) {
    Write-Host "Installing $Distro (WSL2)..."
    wsl --install -d $Distro --no-launch --web-download --version 2 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "WSL2 install failed (virtualization may be off in BIOS). Falling back to WSL1."
      $useWsl2 = $false
    }
  }
  if (-not $useWsl2) {
    Write-Host "Installing $Distro (WSL1 — works without BIOS virtualization)..."
    wsl --install -d $Distro --no-launch --web-download --version 1 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "WSL distro install failed. Enable virtualization in BIOS for WSL2, or see docs/LOCAL_DEV.md" }
  }
} else {
  Write-Host "OK   $Distro already installed"
}

wsl --set-default $Distro 2>&1 | Out-Host

# Smoke test
Write-Host "Smoke test..."
wsl -d $Distro -u root -- bash -lc "echo WSL_OK && uname -a" 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { throw "WSL launch failed after install" }

if (-not $SkipLinuxDeps) {
  $repoWsl = ($Root -replace '\\', '/').Replace('C:', '/mnt/c').Replace('c:', '/mnt/c')
  Write-Host "Installing Linux dev deps (apt, uv, dos2unix)..."
  wsl -d $Distro -u root -- bash -lc "export TRENDALGO_REPO_WIN='$repoWsl'; bash '$repoWsl/scripts/setup-wsl-linux.sh'" 2>&1 | Out-Host
}

Write-Host ""
Write-Host "=== WSL ready ===" -ForegroundColor Green
Write-Host "Default distro: $Distro"
Write-Host "Run repo gates:"
Write-Host "  wsl -d $Distro -- bash -lc `"cd $((($Root -replace '\\','/')).Replace('C:','/mnt/c')) && bash scripts/watch-agent-gates.sh --once --autofix`""
if ($script:RebootNeeded) {
  Write-Warning "Reboot recommended to finish enabling Windows features (then re-run this script if gates fail)."
}
if (-not $PreferWsl2) {
  Write-Host ""
  Write-Host "Note: Using WSL1 because WSL2 needs CPU virtualization in BIOS."
  Write-Host "For WSL2 later: enable Intel VT-x / AMD-V in BIOS, then:"
  Write-Host "  wsl --set-version $Distro 2"
}
