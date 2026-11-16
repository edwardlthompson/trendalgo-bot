# Save CoinMarketCal API key to Windows Credential Manager (PF-H1).
# Prefer an external PowerShell window if Cursor's terminal hides input oddly.
# Usage:  .\scripts\set-calendar-cmc-key.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$secure = Read-Host "Paste CoinMarketCal API key" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
if ([string]::IsNullOrWhiteSpace($plain)) {
  Write-Error "Empty key — aborted."
  exit 1
}

# Pipe key on stdin (no argv) so the secret is not in process command line.
$plain | uv run python scripts/set-calendar-cmc-key.py
$code = $LASTEXITCODE
$plain = $null
[GC]::Collect()
exit $code
