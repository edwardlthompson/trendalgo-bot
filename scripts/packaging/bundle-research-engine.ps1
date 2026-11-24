#Requires -Version 5.1
<#
.SYNOPSIS
  Stage a pinned Python Research Engine next to an Avalonia shell publish folder (ADR-0021).

.DESCRIPTION
  Creates engine/ under the publish directory with a requirements pin note and copies
  src/trendalgo for source-tree official builds. Frozen PyInstaller engine packaging
  remains a follow-on; this script establishes the layout + version handshake files.
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$PublishDir,
  [string]$EngineVersion = ""
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$publish = Resolve-Path $PublishDir
$engineOut = Join-Path $publish "engine"
New-Item -ItemType Directory -Force -Path $engineOut | Out-Null

if (-not $EngineVersion) {
  $pyproject = Get-Content (Join-Path $root "pyproject.toml") -Raw
  if ($pyproject -match 'version\s*=\s*"([^"]+)"') { $EngineVersion = $Matches[1] }
  else { $EngineVersion = "0.0.0-dev" }
}

$src = Join-Path $root "src\trendalgo"
$dest = Join-Path $engineOut "trendalgo"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Copy-Item -Recurse $src $dest

$manifest = @{
  engine_version = $EngineVersion
  protocol_version = 1
  schema_version = 1
  layout = "src-tree"
  bundled_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json
Set-Content -Path (Join-Path $engineOut "engine_manifest.json") -Value $manifest -Encoding utf8

Write-Host "Bundled engine $EngineVersion -> $engineOut"
exit 0
