# CEX / DEX API access limits

> **Sources dated:** 2026-10-19 (vendor docs change — prefer conservative floors in registries).  
> **Related:** [`EXCHANGE_ROADMAP.md`](EXCHANGE_ROADMAP.md) · [`DEX_ROADMAP.md`](DEX_ROADMAP.md) · `config/exchanges.registry.json` · `config/venues.registry.json`

## Rules that never change

- **Keys ≠ live.** Query keys only sync portfolio / dry-run / shadow. Live orders need the owner-signed go-live gate.
- **Never Withdraw / transfer / custody** on any CEX API key.
- **Never put `DEX_SIGNER_KEY` on the device** (host/VPS only per ADR-0011).
- Authenticated CEX calls share a per-venue `RateBudget` (`exchanges/private_budget.py`).

## CEX key scopes

| Venue | Query (portfolio) | Trade (bot) | Forbidden |
|-------|-------------------|-------------|-----------|
| Kraken | Query Funds, Query Open/Closed Orders & Trades | + Create & Modify Orders, Cancel/Close | Withdraw, Deposit, Ledger |
| Binance.US / Binance | Read | Spot trade | Withdraw |
| Coinbase Advanced | View | Trade | Transfer |
| Gemini / Bitstamp / Crypto.com / Bybit / OKX | Read balances + orders | Place/cancel | Withdraw |

Wizard copy: start **query-only**, rotate to trade+query only after shadow + $100 pocket.

## CEX private rate floors (enforced)

| id | min_sync_interval_sec | max_private_calls_per_min | Notes |
|----|----------------------|----------------------------|-------|
| kraken | 15 | 15 | Counter + decay; ccxt `enableRateLimit` |
| binanceus | 15 | 20 | Request weight bucket |
| coinbaseadvanced | 20 | 10 | Advanced Trade quotas |
| gemini | 20 | 10 | |
| bitstamp | 20 | 10 | |
| cryptocom | 20 | 10 | |
| binance | 25 | 20 | Worldwide; H-032 for live |
| bybit | 25 | 20 | |
| okx | 25 | 20 | |

Public OHLCV uses `market/rate_budget.py` separately.

## DEX / RPC

Wallet read only on device: RPC URL + address. No CEX-style API key.

| Venue | min_sync_interval_sec | Notes |
|-------|----------------------|--------|
| ethereum / base / arbitrum / solana | 60 | Free RPC tiers ban tight loops; was 2s |

Backoff on RPC errors; fail soft in UI — no tight retry.

## Key validation probe

Allowlisted methods only: `fetch_balance` / `fetchBalance`. Counts against the venue private budget. Success → green check + dialog (no secret material). Failure → not marked verified.
