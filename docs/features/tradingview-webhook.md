# Feature: tradingview-webhook

> Sprint 4 — secured ingress for TradingView alerts (T4, R-037).

## Acceptance criteria

- ✅ HMAC-SHA256 via `X-Signature` header (`TRADINGVIEW_WEBHOOK_SECRET`)
- ✅ Optional IP allowlist (`TRADINGVIEW_IP_ALLOWLIST`)
- ✅ Rate limit: 30 requests/minute per IP
- ✅ Audit log in `webhook_audit` table
- ✅ Reject unsigned/invalid payloads without executing trades (signal log only)

## Smoke scenario

1. Given API running with secret `test` and allowlist `127.0.0.1`
2. When POST `/api/v1/webhooks/tradingview` with signed JSON `{"pair":"BTC/USD","action":"buy"}`
3. Then response `accepted: true` and audit row `reason=accepted`

## Container map

| Layer | Path |
|-------|------|
| Logic | `src/trendalgo/signals/tradingview.py` |
| API | `src/trendalgo/api/routes/webhooks.py` |
| Tests | `tests/test_signals/test_tradingview.py` |

## Definition of Done

- Unit tests green; `docs/risk-catalog.json` R-037 verification path satisfied

## Notes

- Freqtrade execution wiring deferred to Sprint 5+; MVP logs signal to debug log
- After each AGENT step: `bash scripts/watch-agent-gates.sh --once --autofix`
