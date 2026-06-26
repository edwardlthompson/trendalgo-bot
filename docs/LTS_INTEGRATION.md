# LTS Integration — linear-trend-spotter Boundary

> Sprint 0 research · Sprint 4.5 full absorption (ADR-0006)

## Import boundary (until S4.5 merge)

```
ALLOWED imports into src/trendalgo/lts/:
  - linear_trend_spotter.backtesting.*
  - linear_trend_spotter.scanner.* (read-only adapters)

FORBIDDEN:
  - standalone main.py entrypoint
  - raw notifications module from LTS repo
  - direct Render/cron worker assumptions
```

## Target layout (S4.5)

| LTS source | TrendAlgo destination |
|------------|----------------------|
| Scanner pipeline | `src/trendalgo/scanner/` |
| BacktestDataLoader | `src/trendalgo/lts/backtest.py` |
| qualified_snapshot.json | Preserved contract (O5) |
| SQLite snapshots | Namespaced TrendAlgo DB tables (O3) |

## Parity gate

Before archiving standalone repo:

```bash
bash scripts/lts-parity-check.sh
```

H-014 human approval after exit 0.

## References

- ADR-0006
- R-002, R-013
- `docs/features/opportunity-scanner.md`
