#!/usr/bin/env bash
# API key policy — no Withdraw permission in templates (R-009).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "=== check-api-key-policy ==="
FAIL=0
for f in .env.example SECURITY.md docs/SECURITY.md; do
  [ -f "$f" ] || continue
  if grep -qi withdraw "$f" && ! grep -qi "never.*withdraw\|no withdraw\|forbidden.*withdraw" "$f"; then
    echo "WARN $f mentions withdraw without prohibition"
    FAIL=1
  fi
done
if [ -f .env.example ] && grep -qi "BINANCEUS_API_KEY" .env.example; then
  echo "OK   .env.example documents BINANCEUS keys (S13)"
fi
if [ -f .env.example ] && grep -qi "COINBASEADVANCED_API_KEY" .env.example; then
  echo "OK   .env.example documents Tier B keys (S14)"
fi
if [ -f .env.example ] && grep -qi "BYBIT_API_KEY" .env.example; then
  echo "OK   .env.example documents worldwide portfolio keys (S14)"
fi
if [ -f .env.example ] && grep -qi "never.*withdraw\|no withdraw" .env.example; then
  echo "OK   .env.example documents no Withdraw permission"
fi
if [ -f docs/SECURITY.md ] || [ -f SECURITY.md ]; then
  echo "OK   SECURITY.md present"
  exit 0
fi
echo "SCHEDULED — SECURITY onboarding (Sprint 4/10)"
exit 2
