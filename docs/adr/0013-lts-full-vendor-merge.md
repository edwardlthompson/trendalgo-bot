# ADR-0013: Full LTS vendor merge (dashboard + backtesting)

- **Status:** Accepted
- **Date:** 2026-10-08
- **Supersedes (partially):** ADR-0006 thin native-port path for Scanner UI

## Context

The TrendAlgo Scanner MVP (`ScannerPanel` table + QualifiedSnapshot v2) was not product parity with Linear Trend Spotter’s dialed-in Qualified dashboard (venue rows, sparklines, Best BT / Bot vs B&H, Results modal) or the `backtesting/` strategy sweep library.

## Decision

1. **File-vendor** (copy, **not** git submodule) LTS `docs/dashboard/` → `examples/web/public/lts-dashboard/`.
2. Scanner tab hosts that UI in a full-bleed iframe; config points at TrendAlgo `GET /api/v1/scanner/qualified_public_snapshot.json`.
3. Vendor LTS `backtesting/` + snapshot helpers under `src/trendalgo/lts_vendor/` with import shims (no LTS `main` / `notifications`).
4. Post-scan hook publishes LTS-shaped JSON and optionally runs `run_backtests_for_final_results`, merging `backtest_top_strategies` / `backtest_buy_hold`.
5. TrendAlgo **fleet** Backtest tab (`BacktestPanel` + `fleet_*`) remains a separate interactive Kraken/CCXT path — not deleted, not merged into the LTS engine.

## Consequences

- Provenance: `src/trendalgo/scanner/vendor_manifest.json` (commit SHA, MIT).
- Docs: `docs/LTS_INTEGRATION.md`, `docs/LTS_BACKTESTING.md`.
- CMC / CoinGecko keys enrich live data; without keys, synthetic/sparse snapshot keeps the UI loading.
- H-014 archive of the standalone LTS repo remains a HUMAN gate after parity acceptance.
