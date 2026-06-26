# ADR-0010: Native CCXT Trading Engine

- **Status:** Accepted (Exchange Program)
- **Date:** 2026-06-25
- **Deciders:** Project team
- **Supersedes:** ADR-0001 forward path

## Context

S0–S12 used Freqtrade as the trading engine. The exchange program (S13–S20) requires multi-venue portfolio aggregation worldwide and phased bot trading on US and global CEXs. Maintaining Freqtrade as a parallel engine adds complexity without covering all target venues.

## Decision

1. **Engine:** Native CCXT runner in `src/trendalgo/trading/runner/` — sole trading path.
2. **Strategies:** Runtime contract (`on_candle`, `signal`, `exit`) in `src/trendalgo/strategies/runtime/` — no Freqtrade `IStrategy`.
3. **Backtest:** Reuse S7 `backtest/library.py` via native adapter (CM-1).
4. **Portfolio:** Registry-driven CCXT adapters in `src/trendalgo/exchanges/`.
5. **Freqtrade:** Removed in S15 CM-4 — port signal logic only; delete `user_data/`, FT docker service, FT pip extra.
6. **Default mode:** Dry-run until go-live gate passes (unchanged).

## Strategy runtime contract

| Hook | Purpose |
|------|---------|
| `on_candle` | Update indicators per candle |
| `signal` | Return entry signal or None |
| `exit` | Return True to close position |

Templates register native module paths. Tests use fixture OHLCV — no Freqtrade parity requirement.

## Consequences

- S15 ships native dry-run runner + FT removal in one cutover
- H-031 hard gate before S15 AGENT work
- CI passes without freqtrade installed
- `docs/NATIVE_TRADING.md` replaces FREQTRADE_INTEGRATION.md

## Alternatives considered

| Option | Rejected because |
|--------|------------------|
| Keep Freqtrade optional | Dual engine maintenance; incomplete venue coverage |
| Freqtrade + native hybrid | Complexity; user chose full removal |
| Archive FT in `legacy/` | User: no archive — extract and delete |

## Verification

- CM-4: `rg -i freqtrade` clean in `src/` and `examples/web/`
- CM-1: dry-run order → journal entry
- CM-7: no `withdraw` in `trading/`
