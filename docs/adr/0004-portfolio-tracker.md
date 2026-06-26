# ADR-0004: Portfolio Tracker — CoinStats Replacement

- **Status:** Accepted (Sprint 0)
- **Date:** 2026-06-25

## Context

Operator pays for CoinStats; goal is self-hosted parity with daily P/L and Kraken sync.

## Decision

1. **Replace incrementally** — Kraken read-only CCXT sync first; multi-exchange S8.
2. **Data:** `fetch_balance` + Freqtrade trade DB for cost basis; daily snapshots in SQLite.
3. **Cost basis:** FIFO from closed trades; manual entry for external holdings (S8).
4. **Charts:** Lightweight Charts equity curve; allocation pies in Web UI.
5. **Daily P/L:** APScheduler on VPS; Telegram + PWA; default 8 AM (`America/Puerto_Rico`).
6. **Pause trading ≠ pause tracker** — circuit breaker stops bots; sync continues.

## Consequences

Sprint 5 core; H-015/H-017 gates; `docs/PORTFOLIO_TRACKER.md`.
