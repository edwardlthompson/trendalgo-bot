# CEX / DEX API access limits

> **Sources dated:** 2026-11-12 (CMC product email 2026-11-02 freshness; CEX floors 2026-10-19).
> Vendor docs change — prefer conservative floors in registries.
> **Related:** [`EXCHANGE_ROADMAP.md`](EXCHANGE_ROADMAP.md) · [`DEX_ROADMAP.md`](DEX_ROADMAP.md) · `config/exchanges.registry.json` · `config/venues.registry.json` · [`LTS_BACKTESTING.md`](LTS_BACKTESTING.md)

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

## CoinMarketCap (optional enrichment)

Optional `CMC_API_KEY` — not required for the free Kraken path. Pacing: env `CMC_CALLS_PER_MINUTE` (default **30** via `lts_vendor` settings / `MinIntervalGate`).

### Data freshness (vendor, since 2026-11-02)

Nothing to change in call shapes — responses are fresher. **Credits still bill per call**, so shortening our poll interval multiplies monthly usage.

| Endpoint class | Freshness now | Was |
|----------------|---------------|-----|
| `/v3/cryptocurrency/listings/latest` | every **15s** | 60s |
| `/v1/cryptocurrency/listings/new` (quotes) | every **15s** | 60s |
| `/v1/cryptocurrency/category` (crypto quotes) | every **15s** | 60s |
| `/v3/cryptocurrency/quotes/latest` | **15–25s** | 60s |
| `/v2/simple/price` | **15–25s** | 60s |
| `close` in `/v2/cryptocurrency/ohlcv/latest` | **15–25s** | 10 minutes |
| quotes in `/v1/cryptocurrency/trending/*` (latest, gainers-losers, most-visited) | **15–25s** | (prior vendor cadence) |
### Credit guardrails (ours)

- Prefer **one** bulk listings/quotes call per scan over per-coin chatter.
- Do **not** drop poll interval to 15s “because CMC can” without checking the plan’s **monthly call credits** (Basic free tiers are tight; 4×/min ≈ 4× credits vs 1×/min).
- Keep `CMC_CALLS_PER_MINUTE` as a **ceiling**, not a target — default 30 is already above typical Basic comfort if every slot is used.
- Verify live plan/RPM/credits on [CMC API pricing](https://coinmarketcap.com/api/pricing/) and `/v1/key/info` when a key is set.

## DEX / RPC

Wallet read only on device: RPC URL + address. No CEX-style API key.

| Venue | min_sync_interval_sec | Notes |
|-------|----------------------|--------|
| ethereum / base / arbitrum / solana | 60 | Free RPC tiers ban tight loops; was 2s |
Backoff on RPC errors; fail soft in UI — no tight retry.

## Key validation probe

Allowlisted methods only: `fetch_balance` / `fetchBalance`. Counts against the venue private budget. Success → green check + dialog (no secret material). Failure → not marked verified.
