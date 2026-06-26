# TrendAlgo — L2 production build preview (API :8000 + vite preview)
# Usage: .\scripts\preview-local.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$DataDir = Join-Path $Root "data\dev"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$env:TRENDALGO_DATA_DIR = $DataDir
$env:TRENDALGO_MODE = "dry-run"
$env:TRENDALGO_API_PORT = "8000"

Write-Host "Building web PWA..."
Push-Location (Join-Path $Root "examples\web")
if (-not (Test-Path "node_modules")) { npm ci }
npm run build

Write-Host "Starting API on http://127.0.0.1:8000"
$apiJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    $env:TRENDALGO_DATA_DIR = Join-Path $root "data\dev"
    $env:TRENDALGO_MODE = "dry-run"
    $env:TRENDALGO_API_PORT = "8000"
    python -m trendalgo.api.main
} -ArgumentList $Root

Start-Sleep -Seconds 2
Write-Host "Starting vite preview (default http://localhost:4173)"
Write-Host "Press Ctrl+C to stop."

try {
    npm run preview
}
finally {
    Stop-Job $apiJob -ErrorAction SilentlyContinue
    Remove-Job $apiJob -Force -ErrorAction SilentlyContinue
    Pop-Location
}
