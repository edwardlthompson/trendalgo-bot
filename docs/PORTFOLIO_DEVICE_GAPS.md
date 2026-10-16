# Portfolio device parity vs CoinStats / Delta / Kubera

Inventory for the 2026-10 device Portfolio port (core + advanced).

## Shipped on device

- Net worth hero, daily / realized / unrealized / total P/L, health score, max drawdown
- Equity chart with performance ranges (`1y`…`24h`)
- Holdings: allocation %, cost basis, tags, sort by value, hide dust, CSV export
- Heatmap, snapshot timeline, multi-account strip
- Rebalance suggestions (when targets exist), goals progress, dry-run arbitrage watch
- **Sync from host** via `GET /api/v1/portfolio` into local `portfolio.db` (no exchange keys on device)

## Deferred (out of FOSS local-device brief)

| Feature | Typical in | Why deferred |
| --- | --- | --- |
| Stocks / banks / property / debts | Kubera, Delta multi-asset | Crypto-first product; not ADR-0016 scope |
| Built-in tax engine | CoinTracker, Koinly | CSV export handoff only |
| 100+ chain DeFi / NFT suite | CoinStats | Preview DEX rows only when store has data |
| News / swap / AI research agent | CoinStats | AI Strategies tab removed from nav |
| Push notification inbox product | CoinStats | Prefer existing device notify prefs |

## Source references

- Retired PWA: `examples/web/src/portfolio/` (backup `trendalgo-retired-pwa-2026-10-10`)
- API: `src/trendalgo/api/routes/portfolio.py`, `portfolio_advanced.py`
- Device: `src/trendalgo/device/views/portfolio_page.py`, `portfolio_advanced_panel.py`
