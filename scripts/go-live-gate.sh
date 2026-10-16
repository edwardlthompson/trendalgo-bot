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
  EX="${EXCHANGE:-all}"
  # H2/H3: the approval is an owner-signed command to the host. The CLI writes the audit line
  # (data/audit/go-live.jsonl) only after the host accepts it. This script never writes the
  # exchange store directly. Requires TRENDALGO_OWNER_ID and TRENDALGO_OWNER_SECRET in the env.
  if ! command -v uv >/dev/null 2>&1; then
    echo "FAIL uv not found — install uv, then re-run --approve"
    exit 1
  fi
  if ! uv run python -m trendalgo.trading.go_live_cli --exchange "$EX"; then
    echo "FAIL go-live refused or host unreachable (see above); no approval recorded"
    exit 1
  fi
  echo "HUMAN: confirm exchange IP whitelist and position caps in exchange UI"
  exit 0
fi

echo "OK   go-live check-only (use --approve --exchange kraken after HUMAN whitelist)"
exit $ERRORS
