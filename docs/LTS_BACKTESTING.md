# LTS backtesting library (vendored in TrendAlgo)

Adapted from Linear Trend Spotter `docs/BACKTESTING_LIBRARY.md`. Package root: `src/trendalgo/lts_vendor/backtesting/`.

## Role

Scanner **Results** modal data comes from this library (hill-climb + TSL sweep). The TrendAlgo **Backtest** tab is a separate fleet interactive path — do not merge the engines.

## Public entry points

| Symbol | Role |
|--------|------|
| `BacktestDataLoader` | Loads 1h OHLCV (**Kraken USD spot first** via shim → Polygon → CMC; coin-specific synthetic fallback), resamples to `1h` / `4h` / `1d` |
| `run_backtests_for_final_results` | Orchestrates optimizer for qualified coins → `backtest_results.json` |
| `notification_rows_for_symbol` | Shapes `backtest_top_strategies` / `backtest_buy_hold` for the public snapshot |
| `BacktestLoaderParams` / `BacktestRunnerParams` | Constructor-injected knobs (no LTS `config.json` required) |

Call `trendalgo.lts_vendor.install_import_shims()` before importing loader/runner so `api.*` / `database.cache` / `config.settings` resolve to TrendAlgo shims.

## Host integration

1. After a scanner pipeline run, `trendalgo.lts_vendor.bridge.publish_from_v2_snapshot` maps v2 opportunities → LTS coin rows.
2. Optional sweep (`BACKTEST_ENABLED=1`) writes artifacts under `TRENDALGO_DATA_DIR`:
   - `backtest_results.json`
   - `lts_backtest_checkpoint_<digest>.json` (one per sweep configuration; see TA-Lib)
   - `lts_backtest_telemetry.jsonl`
3. Snapshot merge fills `backtest_top_strategies` / `backtest_buy_hold` on each coin.
4. Dashboard fetches `GET /api/v1/scanner/qualified_public_snapshot.json`.
5. Optional `POST /api/v1/scanner/backtest/run` queues a sweep without a full rescan.

## Import boundaries

Vendored `backtesting/**/*.py` must not import `main` or `notifications` (enforced in `tests/test_lts_vendor/test_backtesting_engine.py`).

## Env knobs

See `.env.example` (`CMC_API_KEY`, `COINGECKO_API_KEY`, `BACKTEST_*`). Defaults match upstream LTS: empty `BACKTEST_INDICATORS` → full registry (RSI…Heikin Ashi) + B&H per timeframe, `BACKTEST_MAX_COINS_PER_RUN=0` (all qualified), TSL 2–20 step 2, `1h`/`4h`. Production sweeps pull Kraken hourly bars per symbol so B&H / strategy `%` differ by coin. CI / `TRENDALGO_MARKET_SOURCE=synthetic` uses coin-shaped synthetic OHLCV (not scale-invariant).

## Workers, price cache, and synthetic candles

- **Workers:** `BACKTEST_PARALLEL_WORKERS` defaults to `8` (config and desktop shell; `.env` overrides). Each worker processes one coin at a time.
- **Price cache:** 1h candles persist in `lts_price_cache.db` under `TRENDALGO_DATA_DIR`. The file is SQLite in WAL mode, shared by all workers. An entry expires `CACHE_PRICE_HOURS` (default 12) after fetch. A 1h series is reused only while its newest candle opened within the last 3 hours, so a truncated download is never trusted. Back-to-back sweeps reuse the data. A sweep after a longer gap downloads again. Delete the file to force a full refresh. If the file cannot be opened or written, the cache keeps working in memory and logs a warning.
- **Synthetic candles (opt-in):** when Kraken returns no candles for a coin, the coin is skipped with reason `no_intraday_ohlcv`, and its progress line says so (for example `(no_intraday_ohlcv x2)`). The Polygon and CMC fallbacks are stubs in this build and add no candles. Set `BACKTEST_ALLOW_SYNTHETIC=1` (also `true`, `yes`, or `on`) to backtest coin-shaped synthetic candles instead. Their loader source is `synthetic`, and they are never written to the cache, so the next run retries Kraken.
- **Engine:** `run_backtest` runs its bar loop on plain Python lists with identical float arithmetic. `tests/test_lts_vendor/test_engine_golden.py` pins 132 scenario digests from before the rewrite (`tests/test_lts_vendor/fixtures/engine_golden.json`). Regenerate the fixture only for an intentional engine change, with `python tests/test_lts_vendor/engine_golden_support.py`, and review the diff.
- **Progress and ETA:** the scan feed counts backtests, not coins. One backtest is one strategy (an indicator, or B&H) on one timeframe of one coin, so a sweep runs `coins × timeframes × (indicators + 1)` of them. Pool workers report each finished backtest through a queue (`backtest_counter.py`), and every coin ends with a close marker, so a failed or timed-out coin is counted once and the count never passes the total. The bar reads `N/total backtests`. A line is logged at every 10% with the time left, estimated from the pace so far. The first estimate runs high because it includes data loading.

## TA-Lib

Six of the twelve registry indicators need the native `TA-Lib` binding: Stochastic, CCI, Ultimate Oscillator, MFI, ADX, and Parabolic SAR. The other six (RSI, MACD, EMA/SMA Crossover, Bollinger %B, Heikin Ashi) run on pandas. The desktop extra (`uv run --extra desktop`) and the device extra (`uv run --extra device`) install `TA-Lib`, so a sweep there covers the full registry. The CI python job syncs the `dev` and `device` extras (2026-10-10), so `talib` is present there and the six run in CI. Where `talib` is missing, the six are reported as skipped, not dropped silently. The device extra includes `TA-Lib` because the golden trade lists in `tests/test_lts_vendor` were generated with it.

- Every sweep start probes each indicator. One that cannot run emits `bt_indicator_unavailable`. The scan progress feed shows it as a warning (for example `Stochastic skipped: TA-Lib required for stochastic_signals`), and that sweep leaves it out.
- The checkpoint is keyed to the sweep (indicators, timeframes, TSL grid, TA-Lib availability) as `lts_backtest_checkpoint_<digest>.json`. A checkpoint written without TA-Lib is never resumed into a run that has it.
