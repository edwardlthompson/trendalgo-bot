# Feature: Market Context

> Pair-level traditional market read on Backtest + Scanner Results — separate from strategy tables.
> Checklist: ✅ done.

## Acceptance criteria

- ✅ Dedicated Market Context pane (Signal / Levels / Risk / Structure) above strategy results on Backtest tab
- ✅ Same pane in Scanner Results dialog; never mixed into `BACKTEST_RESULT_HEADERS`
- ✅ Scanner Qualified **Market Context top 10** band: always highest consensus scores on the filtered board (+ top TA net% when All-TA ran)
- ✅ Seven classic pivots (S1–S3, PP, R1–R3) with strength; consensus −2…+2 → Buy/Sell/Neutral + confidence
- ✅ Regime labels: Trending Up/Down, Ranging, Volatile, Compressing (mapped from Sauce detector)
- ✅ Risk: ATR×1.5 stop distance; R:R to R1 and R2
- ✅ Extras: nearest S/R distance, confluence, VWAP, VP lite, N-bar extension, BTC corr, spread proxy
- ✅ Soft-fail empty/loading/error; collapse preference persisted
- ✅ Causal pivot/VWAP/VP keys in Secret Sauce Lab (primary + residual search) and Sauce TA pivot gates (fee-Net lift only; no consensus dump)
- ✅ i18n strings in `strings.py`; Show Chart overlays when context present

## Smoke scenario

1. _Given_ Device Backtest All-TA on a liquid pair
2. _When_ scan finishes
3. _Then_ Market Context band fills above the strategy table (not as rows)
4. _And_ Scanner Results for that coin shows the same band above the strategy sheet

## Container map

| Layer | Path |
|-------|------|
| Logic | `src/trendalgo/analytics/` (`classic_pivots`, `indicator_consensus`, `market_context`, …) |
| Lab | `src/trendalgo/backtest/secret_sauce_pivots.py` (+ structure merge) |
| View | `src/trendalgo/device/views/market_context_pane.py`, `buy_picks_pane.py` |
| Rank | `src/trendalgo/device/buy_picks.py` |
| Wiring | `backtest_page.py`, `scanner_results.py`, `scanner_page.py`, `pair_strategy_scan.py` ≤10 lines each |
| Tests | `tests/test_analytics/`, `tests/test_device/test_market_context_pane.py`, `test_buy_picks*.py` |

## Constants

- Stop multiple: **ATR×1.5** (long framing) — shared by pane R:R and Lab demote filter
- Extension window: **90 bars**
- Pivot period: prior completed day (or prior N bars of active TF) — causal only

## Notes

- Strength column remains strategy win-rate quality — Signal zone uses **Confidence**
- Oracle-gap Phase 2 holdout remains follow-on; new Lab keys stay fee-honest and sparse
