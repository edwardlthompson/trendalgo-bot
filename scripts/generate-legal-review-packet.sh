#!/usr/bin/env bash
# Bundle legal ADRs + posture docs for Legal Research Desk / Tier A–B (ADR-0020).
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
  echo "> **Not legal advice.** Packet for founder Tier A residual-risk review and optional counsel (Tier B / H-006b)."
  echo ""
  echo "## Scope"
  echo "- **Tier A:** owner-only + FOSS / source-available distribution (H-006 / H-022 / H-023)"
  echo "- **Tier B:** non-owner commercial billing deferred (H-006b)"
  echo "- Performance-contingent **software license** framing (not payment processing)"
  echo "- User-initiated crypto settlement only; no auto-withdraw"
  echo "- No KYC; pseudonymous install UUID; no custodial funds"
  echo ""
  echo "## Included documents"
  for f in \
    docs/adr/0007-legal-framework.md \
    docs/adr/0008-legal-safe-monetization.md \
    docs/adr/0017-multi-user-monetization.md \
    docs/adr/0018-elastic-license-v2.md \
    docs/adr/0020-legal-research-desk.md \
    docs/adr/0009-ai-recommended-strategies.md \
    docs/LEGAL.md \
    docs/LEGAL_SAFETY.md \
    docs/MONETIZATION.md \
    docs/LICENSE_MODEL.md \
    docs/AI_STRATEGIES.md \
    docs/RISK_REGISTER.md \
    docs/FOUNDER_LEGAL_POSTURE.md \
    TERMS.md \
    BUILD_PLAN.md; do
    if [ -f "$f" ]; then
      echo ""
      echo "---"
      echo "## Source: \`$f\`"
      echo ""
      cat "$f"
    else
      echo ""
      echo "---"
      echo "## MISSING: \`$f\`"
    fi
  done
  echo ""
  echo "## Checklist (Tier A founder)"
  echo "- [ ] LEGAL_SAFETY Never/Always still match the product"
  echo "- [ ] TERMS.md is ELv2 / software-tool; fee enrollment marked Tier B"
  echo "- [ ] FOUNDER_LEGAL_POSTURE.md has Accepted-scope + Accepted-date"
  echo "- [ ] CI: \`bash scripts/check-legal-compliance.sh\`"
  echo ""
  echo "## Checklist (Tier B counsel / clinic — H-006b)"
  echo "- [ ] Performance license framing vs MSB / money transmission (PR/US)"
  echo "- [ ] Adviser-style / performance-fee rules before non-owner charges"
  echo "- [ ] User-initiated settlement copy — no auto-collect claims"
  echo "- [ ] Data minimization — no IP/email in consent log"
} > "$OUT"

echo "OK   wrote $OUT"
echo "Tier A: python scripts/founder_gate.py approve H-006 --note \"residual-risk owner-only+foss …\""
echo "Tier B: see docs/legal-desk/when-to-get-counsel.md (H-006b)"
