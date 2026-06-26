# LTS Absorption — Opportunity Scanner (ADR-0006)

> Sprint 4.5 complete · Standalone `linear-trend-spotter` enters deprecation path.

## Strategy

TrendAlgo absorbed LTS as a **native port** in `src/trendalgo/scanner/` — no git submodule (requires `[HUMAN]` approval per destructive-ops policy). Module mapping is recorded in `src/trendalgo/scanner/vendor_manifest.json`.

## Module map

| LTS concept | TrendAlgo module |
|-------------|------------------|
| Scanner pipeline (volume, gain, uniformity, entry/exit) | `scanner/pipeline.py` |
| `qualified_snapshot.json` contract | `scanner/snapshot.py` |
| SQLite snapshots | `scanner.db` via `scanner/store.py` |
| Scheduler / cron worker | `scanner/scheduler.py` (APScheduler) |
| BacktestDataLoader | `scanner/backtest.py`, `lts/backtest.py` |
| Alert tiers | `scanner/alerts.py` |
| Bot whitelist feed | `scanner/watchlist_bridge.py` |
| Freqtrade mixin | `scanner/mixins.py` (`OpportunityScannerMixin`) |

## API surface

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/scanner/snapshot` | Latest qualified snapshot (O5) |
| `POST /api/v1/scanner/run` | Trigger scan + persist |
| `GET/PUT /api/v1/scanner/settings` | Scan frequency + universe filters (O15) |
| `GET/POST /api/v1/scanner/watchlist` | Pin pairs |
| `GET /api/v1/scanner/pairs-for-bot` | Freqtrade whitelist bridge (O8) |

## API credit strategy (O4)

- **Kraken spot MVP:** synthetic/sample market data in dry-run; live OHLCV via CCXT in Sprint 8.
- **Scheduler:** APScheduler interval job on VPS — replaces standalone Render worker.
- **No external scanner SaaS** — all logic self-hosted.

## Parity gate

```bash
bash scripts/lts-parity-check.sh
bash scripts/check_scanner_imports.sh
```

Exit 0 required before archiving standalone repo. **H-014** human approval remains in [`docs/HUMAN_BACKLOG.md`](HUMAN_BACKLOG.md).

## Standalone repo deprecation README template

Copy to `linear-trend-spotter/README.md` when parity passes:

```markdown
# linear-trend-spotter — DEPRECATED

Development has moved into [TrendAlgo Bot](https://github.com/edwardlthompson/trendalgo-bot)
under `src/trendalgo/scanner/`.

- Scanner UI: TrendAlgo PWA → Scanner tab
- API: `/api/v1/scanner/*`
- Parity validation: `bash scripts/lts-parity-check.sh` in trendalgo-bot

This repository is archived. Do not open new issues here.
```

## References

- ADR-0006
- R-002, R-013
- `docs/LTS_INTEGRATION.md`
- `docs/features/opportunity-scanner.md`
