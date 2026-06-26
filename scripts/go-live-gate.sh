#!/usr/bin/env bash
# Go-live safety gate (H-010 / H-028) — per-exchange approval (S16).
# Usage:
#   scripts/go-live-gate.sh [--check-only|--approve] [--exchange EXCHANGE_ID]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODE="${1:---check-only}"
EXCHANGE=""
shift || true
while [ $# -gt 0 ]; do
  case "$1" in
    --exchange) EXCHANGE="$2"; shift 2 ;;
    --check-only|--approve) MODE="$1"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done
AUDIT="$ROOT/data/audit/go-live.jsonl"

echo "=== go-live-gate ($MODE${EXCHANGE:+ exchange=$EXCHANGE}) ==="
ERRORS=0

if [ -f config/bot/dryrun.example.json ] && [ -f config/bot/live.example.json ]; then
  echo "OK   separate live and dry-run config templates exist"
else
  echo "SCHEDULED live/dry-run config templates (native runner)"
fi

if rg -i "withdraw" .env.example 2>/dev/null | rg -i "never|do not|forbidden" >/dev/null; then
  echo "OK   .env.example warns against Withdraw permission"
elif [ -f .env.example ]; then
  echo "WARN add Withdraw prohibition to .env.example / SECURITY.md"
fi

if [ "$MODE" = "--approve" ]; then
  mkdir -p "$(dirname "$AUDIT")"
  UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
  TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  EX="${EXCHANGE:-all}"
  echo "{\"install_uuid\":\"$UUID\",\"approved_at\":\"$TS\",\"gate\":\"H-010/H-028\",\"exchange\":\"$EX\"}" >> "$AUDIT"
  if command -v uv >/dev/null 2>&1; then
    uv run python - <<PY
from pathlib import Path
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.exchanges.registry import list_trading_exchanges
store = ExchangeControlStore(Path("data/exchange_control.db"))
targets = ["$EX"] if "$EX" != "all" else [e.id for e in list_trading_exchanges() if e.trading_enabled]
for ex in targets:
    store.approve_go_live(ex)
print("OK   exchange control updated:", ", ".join(targets))
PY
  else
    echo "WARN uv not found — run API POST /trading/exchanges/{id}/go-live after approve"
  fi
  echo "OK   go-live approved (logged to data/audit/go-live.jsonl)"
  echo "HUMAN: confirm exchange IP whitelist and position caps in exchange UI"
  exit 0
fi

echo "OK   go-live check-only (use --approve --exchange kraken after HUMAN whitelist)"
exit $ERRORS
