#!/usr/bin/env bash
# Bundle ADR-0007/0008 + legal docs for attorney review (H-006).
# Usage: scripts/generate-legal-review-packet.sh [output.md]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="${1:-docs/legal-review-packet.md}"

echo "=== generate-legal-review-packet ==="
mkdir -p "$(dirname "$OUT")"

{
  echo "# TrendAlgo Bot — Legal Review Packet"
  echo ""
  echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "## Scope for attorney (H-006 / H-023)"
  echo "- Performance-contingent **software license** (not payment processing)"
  echo "- User-initiated crypto settlement only; no auto-withdraw"
  echo "- No KYC; pseudonymous install UUID; no custodial funds"
  echo ""
  echo "## Included documents"
  for f in \
    docs/adr/0009-ai-recommended-strategies.md \
    docs/AI_STRATEGIES.md \
    docs/RISK_REGISTER.md \
    BUILD_PLAN.md; do
    if [ -f "$f" ]; then
      echo ""
      echo "---"
      echo "## Source: \`$f\`"
      echo ""
      cat "$f"
    fi
  done
  echo ""
  echo "## Checklist for counsel"
  echo "- [ ] Performance license framing vs MSB / money transmission (PR/US)"
  echo "- [ ] TERMS.md wording — tool only, not investment advice"
  echo "- [ ] User-initiated settlement copy — no auto-collect claims"
  echo "- [ ] Data minimization — no IP/email in consent log"
} > "$OUT"

echo "OK   wrote $OUT"
echo "Backlog: bash scripts/founder-gate.sh backlog H-006 --reason 'awaiting attorney review'"
