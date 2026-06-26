# Feature: fee-settlement

> M2 seed — idempotency on trade-close fee hooks (R-014). Full settlement UI in Sprint 10.

## Acceptance criteria

- ✅ **Idempotency:** `fee_ledger_hooks.idempotency_key` is UNIQUE; duplicate inserts return `False` without double-charging logic
- ✅ **Trade journal:** SQLite `trades` table logs signal source + rationale per closed trade
- 🔲 User-visible settlement UI (Sprint 10)
- 🔲 Offline/error behavior for billing module (Sprint 10)

## Idempotency key format (R-014)

```
close:{exchange_trade_id}:{close_timestamp_utc}
```

Example: `close:kraken-1:2024-01-01T12:00:00+00:00`

Implementation: `src/trendalgo/risk/journal.py` — `TradeJournal.record_fee_hook()`.

Verification: `tests/test_journal/test_journal.py::test_journal_and_idempotency`.

## Smoke scenario

1. Given a closed trade with `exchange_trade_id=kraken-1`
2. When `record_fee_hook` is called twice with the same idempotency key
3. Then the second call returns `False` and only one row exists in `fee_ledger_hooks`

## Container map

| Layer | Path |
|-------|------|
| Logic | `src/trendalgo/risk/journal.py` |
| Tests | `tests/test_journal/` |
| Wiring | Freqtrade close hook (Sprint 4+) |

## Definition of Done

- Sprint 2: journal + idempotency seed ✅
- Sprint 10: performance license settlement + user-initiated payment

## Notes

- ADR-0005, ADR-0008 — calculation-only; no custodial settlement in MVP
- After each AGENT step: `bash scripts/watch-agent-gates.sh --once --autofix`
