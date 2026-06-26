# Native Trading Engine

> **Replaces:** [`docs/FREQTRADE_INTEGRATION.md`](FREQTRADE_INTEGRATION.md) (removed S15 CM-4)
> **ADR:** [`docs/adr/0010-ccxt-native-engine.md`](adr/0010-ccxt-native-engine.md)

## Overview

TrendAlgo uses a **native CCXT trading runner** — not Freqtrade. Strategies implement a small runtime contract; the runner handles order lifecycle, dry-run simulation, and journal integration.

| Component | Path |
|-----------|------|
| Runner | `src/trendalgo/trading/runner/` |
| Strategy runtime | `src/trendalgo/strategies/runtime/` |
| Backtest | `src/trendalgo/backtest/library.py` + `native_adapter.py` |
| Exchange access | `src/trendalgo/exchanges/` |

## Strategy runtime contract (CM-2)

Strategies expose hooks — no Freqtrade `IStrategy`:

```python
class StrategyRuntime(Protocol):
    def on_candle(self, candle: Candle, ctx: StrategyContext) -> None: ...
    def signal(self, ctx: StrategyContext) -> Signal | None: ...
    def exit(self, ctx: StrategyContext, position: Position) -> bool: ...
```

Templates in `src/trendalgo/templates/registry.py` point to native modules under `strategies/runtime/`.

## Modes

| Mode | Env | Behavior |
|------|-----|----------|
| Dry-run | `TRENDALGO_MODE=dry-run` | Simulated fills; no exchange orders |
| Live | `TRENDALGO_MODE=live` | Real orders after `go-live-gate.sh --approve` |

## Multi-exchange

- **Portfolio:** CCXT read-only via registry (see [`EXCHANGE_ROADMAP.md`](EXCHANGE_ROADMAP.md)).
- **Trading:** One runner instance per bot; exchange from registry + bot config.
- **Go-live:** H-010/H-028 per exchange.
- **Ops (9 venues, ack workflow, incidents):** [`docs/RUNBOOK.md`](RUNBOOK.md) § Multi-venue trading ops (Phase 2, S20).

## Backtest & optimize

- Backtests use S7 `backtest/library.py` via `trading/backtest/native_adapter.py` (CM-1).
- Walk-forward / Monte Carlo: S7 `optimize/` wired to native path (CM-3, S17).
- No Freqtrade hyperopt CLI.

## Risk

- `src/trendalgo/risk/` enforces limits before live enable.
- Order module: create/cancel/fetch only — no withdraw (CM-7).

## Local dev

See [`docs/LOCAL_DEV.md`](LOCAL_DEV.md). After S15, bot dashboard shows `engine=native`.

## Migration note

S0–S12 Freqtrade work informed the native design. Physical FT artifacts are deleted in **S15 CM-4** — there is no legacy Freqtrade mode.
