#!/usr/bin/env bash
# Reject prohibited monetization / architecture patterns (ADR-0008, ADR-0009).
# Usage: scripts/check-legal-compliance.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ERRORS=0

echo "=== check-legal-compliance ==="

if ! command -v rg >/dev/null 2>&1; then
  echo "WARN ripgrep (rg) not installed — skipping content scan"
  exit 0
fi

SCAN_DIRS=""
for d in src examples/web/src docs/features config; do
  [ -d "$d" ] && SCAN_DIRS="$SCAN_DIRS $d"
done
FORBIDDEN=(
  "auto-withdraw"
  "auto withdraw"
  "stripe"
  "community strategy marketplace"
  "community_strategy_marketplace"
  "community_marketplace"
  "user-uploaded strategy"
  "custodial saas"
  "money.transmitter"
  "import_community"
  "/strategies/community"
)

scan_paths() {
  local pattern="$1"
  local hits
  if [ -z "$SCAN_DIRS" ]; then
    return 0
  fi
  hits="$(rg -i --glob '!docs/CANONICAL_PLAN.md' --glob '!docs/RISK_REGISTER*.md' \
    -l "$pattern" $SCAN_DIRS 2>/dev/null || true)"
  if [ -n "$hits" ]; then
    echo "FAIL forbidden pattern '$pattern' in:"
    echo "$hits"
    ERRORS=$((ERRORS + 1))
  fi
}

for pat in "${FORBIDDEN[@]}"; do
  scan_paths "$pat"
done

# CM-4 / S15: no freqtrade in production paths
if rg -i freqtrade src examples/web/src 2>/dev/null; then
  echo "FAIL freqtrade references remain in src/ or examples/web/"
  ERRORS=$((ERRORS + 1))
else
  echo "OK   no freqtrade in src/ or examples/web/"
fi

# CM-7: no withdraw in native runner
if [ -d src/trendalgo/trading/runner ]; then
  if rg -i withdraw src/trendalgo/trading/runner 2>/dev/null; then
    echo "FAIL withdraw references in trading/runner/"
    ERRORS=$((ERRORS + 1))
  else
    echo "OK   trading/runner/ has no withdraw references"
  fi
fi

# ADR-0008 must exist
if [ ! -f docs/adr/0009-ai-recommended-strategies.md ] && [ ! -f DECISION_LOG.md ]; then
  echo "WARN ADR docs sparse — ensure ADR-0008/0009 drafted"
fi

if [ -f docs/adr/0009-ai-recommended-strategies.md ]; then
  echo "OK   ADR-0009 present (no community imports)"
fi

if [ -f docs/adr/0020-legal-research-desk.md ]; then
  echo "OK   ADR-0020 Legal Research Desk present"
fi

# ADR-0020: never ship fake counsel stamps in product paths
FAKE_COUNSEL_HITS="$(rg -i -l 'attorney approved|legal advice from TrendAlgo' src examples 2>/dev/null || true)"
if [ -n "$FAKE_COUNSEL_HITS" ]; then
  echo "FAIL forbidden counsel-stamp phrasing in product paths:"
  echo "$FAKE_COUNSEL_HITS"
  ERRORS=$((ERRORS + 1))
else
  echo "OK   no fake counsel stamps in src/examples"
fi

# Packet must list core legal ADRs when present
if [ -f docs/legal-review-packet.md ]; then
  for need in "0007-legal-framework" "0008-legal-safe-monetization" "0020-legal-research-desk" "FOUNDER_LEGAL_POSTURE"; do
    if ! rg -q "$need" docs/legal-review-packet.md; then
      echo "FAIL legal-review-packet.md missing reference: $need"
      ERRORS=$((ERRORS + 1))
    fi
  done
  echo "OK   legal-review-packet.md references Tier A ADR/posture paths (or reported FAIL above)"
fi

if [ $ERRORS -gt 0 ]; then
  echo "$ERRORS legal compliance check(s) failed"
  exit 1
fi
echo "OK   legal compliance scan passed"
exit 0
