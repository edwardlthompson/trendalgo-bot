# ADR-0001: Freqtrade-as-Engine, Kraken Spot MVP

- **Status:** Superseded by [ADR-0010](0010-ccxt-native-engine.md) (2026-06-25)
- **Date:** 2026-06-25
- **Deciders:** Project team

## Context

TrendAlgo Bot needs a proven trading engine without maintaining a full exchange integration fork. MVP targets Kraken spot only; extension layer adds risk, scanner, portfolio, and billing.

## Decision

1. **Engine:** Freqtrade installed via pip pin in root `pyproject.toml`; configs/strategies in `user_data/`.
2. **Architecture:** **Hexagonal (ports & adapters)** — domain in `src/trendalgo/`, Freqtrade/CCXT as adapters.
3. **Exchange MVP:** Kraken spot; pair naming `BTC/USD` (not USDT on Kraken).
4. **Database MVP:** SQLite co-located on VPS; Postgres documented for S12.
5. **Default mode:** Dry-run until go-live gate passes.
6. **Upgrade path:** Bump Freqtrade pin + regression tests — never fork upstream.

## Consequences

- Sprint 1 wires Freqtrade dry-run + RPC
- `src/trendalgo/risk/` enforces limits before live config load
- CI runs without live API keys (mock/dry-run)

## Alternatives Considered

| Option | Rejected because |
|--------|------------------|
| Fork Freqtrade | Maintenance burden; lose upstream fixes |
| Custom CCXT bot only | Reinvent order lifecycle, backtest, strategy interface |
| Multi-exchange MVP | Scope; Kraken first per BUILD_PLAN |
