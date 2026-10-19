# Feature: Oracle max-gain, Alerts tabs, allocation UX

> Sprint ORACLE-1. Checklist: 🔲 open · ✅ done · ❌ blocked.

## Acceptance criteria

- ✅ 30D backtests show an `ORACLE_MAX` / "Oracle max" baseline (long-only trough→peak) beside B&H; Perfect Strategies filter unchanged
- ✅ "Derive rule from oracle" mines a local `GEN_ORACLE_*` composite rule (optional Ollama name only)
- ✅ Watchlist leave alerts cite concrete floor failures from last coin snapshot
- ✅ Alerts page has Logs / Entered / Left / Trades tabs; notify prefs are Windows×Telegram per kind
- ✅ Category allocation uses 3:1 chart:legend stretch with Qt legend hidden; Coin ring has no center label
- ✅ UX inventory rows landed in BUILD_PLAN for follow-up (UX-ALLOC-3, UX-DASH-*, UX-BT tooltip polish)

## Smoke scenario

1. _Given_ Device Backtest after All-TA on a liquid pair
2. _When_ results load
3. _Then_ B&H and Oracle max rows appear; Derive rule shows a GEN summary or honest empty; Alerts tabs filter history; Settings notify grid saves.

## Container map

| Layer | Path |
|-------|------|
| Logic | `src/trendalgo/backtest/ta_simulator.py`, `oracle_pattern_mine.py`, `ta_fleet.py` |
| Alerts | `scanner_alert_diff.py`, `scanner_alerts_store.py`, `notify_prefs.py`, `alert_dispatch.py` |
| View | `alerts_page.py`, `notify_settings.py`, `allocation_modules.py`, `backtest_page.py` |
| Tests | `tests/test_backtest/test_oracle_max.py`, `tests/test_device/test_scanner_alert_diff.py` |

## Definition of Done

- Unit tests for oracle %, fees, leave reasons, prefs matrix
- `watch-agent-gates --once --autofix --scope auto` green after AGENT steps
- ADR-0009: no marketplace upload of GEN rules

## Notes

- GEN rules always `requires_backtest: true`; operator-local only
- Logs default Windows toast **off** to avoid spam
