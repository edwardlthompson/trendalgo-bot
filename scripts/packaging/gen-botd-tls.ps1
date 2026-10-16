# Generate a self-signed TLS cert for botd on :8443 and print the SHA-256 pin for Settings.
# Usage (from repo root): .\scripts\packaging\gen-botd-tls.ps1 -OutDir .\docker\secrets
param(
  [string]$OutDir = "docker/secrets",
  [string]$CommonName = "botd.local"
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$key = Join-Path $OutDir "botd.key"
$crt = Join-Path $OutDir "botd.crt"
openssl req -x509 -newkey rsa:2048 -nodes -keyout $key -out $crt -days 825 -subj "/CN=$CommonName"
$pin = (openssl x509 -in $crt -noout -fingerprint -sha256) -replace "SHA256 Fingerprint=", "" -replace ":", ""
Write-Host "Certificate: $crt"
Write-Host "Private key: $key"
Write-Host "Paste this SHA-256 pin into device Settings (cert_sha256):"
Write-Host $pin.ToLower()
