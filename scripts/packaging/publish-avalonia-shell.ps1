#Requires -Version 5.1
<#
.SYNOPSIS
  Publish TrendAlgo.Shell for win-x64 / linux-x64 / osx-arm64 and bundle the Research Engine (ADR-0021 AV-07).
#>
param(
  [ValidateSet("win-x64", "linux-x64", "osx-arm64", "all")]
  [string]$Rid = "win-x64",
  [string]$Configuration = "Release",
  [switch]$SkipBundle
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$proj = Join-Path $root "shell\TrendAlgo.Shell\TrendAlgo.Shell.csproj"
$bundle = Join-Path $PSScriptRoot "bundle-research-engine.ps1"

if (-not (Test-Path $proj)) {
  throw "Missing Avalonia project: $proj"
}

$rids = if ($Rid -eq "all") { @("win-x64", "linux-x64", "osx-arm64") } else { @($Rid) }

foreach ($r in $rids) {
  $out = Join-Path $root "dist\shell\$r"
  Write-Host "Publishing $r -> $out"
  New-Item -ItemType Directory -Force -Path $out | Out-Null
  dotnet publish $proj -c $Configuration -r $r --self-contained true -o $out
  if (-not $SkipBundle) {
    & $bundle -PublishDir $out
  }
  Write-Host "OK $r"
}

Write-Host "Done. Outputs under dist/shell/"
exit 0
