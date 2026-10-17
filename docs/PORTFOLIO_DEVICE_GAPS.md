# Dashboard device parity vs CoinStats / Delta / Kubera

Inventory for the 2026-10 modular Dashboard (ex-Portfolio tab).

## Shipped on device

- Nav label **Dashboard**; modular multi-page snap-to-grid canvas (magnetic DnD, adjustable cols/rows)
- Modules: Total Worth, PL Insights, Assets (sort chips), Portfolio Value / Cumulative & Daily P/L / vs Market, Coin & category allocation, heatmap, fees, flows, orders/positions, gainers/losers, competition extras (risk, drawdown, cash drag, …)
- Per-module and per-page PNG export
- Events Calendar + Calendar API wizard (CoinMarketCal + Coindar official APIs; CredMgr keys)
- Sync from host, Top-20 demo, holdings CSV export

## Deferred (out of FOSS local-device brief)

| Feature | Typical in | Why deferred |
| --- | --- | --- |
| Stocks / banks / property / debts | Kubera, Delta multi-asset | Crypto-first product; not ADR-0016 scope |
| Built-in tax engine | CoinTracker, Koinly | CSV export / tax-lots summary only |
| CryptoCraft calendar scrape | CryptoCraft | No official API; ToS/fragility — revisit if they publish one |
| 100+ chain DeFi / NFT suite | CoinStats | Preview when store has data |
| News / swap / AI research agent | CoinStats | Out of local FOSS brief |
| BTC/ETH quote conversion chips | CoinStats | USD active until rates module exists |
| Live multi-exchange Sync All | CoinStats | Host sync + local reload; no exchange keys on device |
## Source references

- Device: `src/trendalgo/device/views/portfolio_page.py`, `views/modules/`, `calendar/`
- Spec: `docs/features/portfolio-modules.md`
- API: `src/trendalgo/api/routes/portfolio.py`, `portfolio_advanced.py`
