# Support matrix (honest)

Machine source: [`src/trendalgo/device/data/support_matrix.json`](../src/trendalgo/device/data/support_matrix.json).
All-TA categories: [`src/trendalgo/device/data/ta_strategy_categories.json`](../src/trendalgo/device/data/ta_strategy_categories.json).

This is what the device UI and README claim. Do not invent checkmarks.

| Venue | Portfolio | Public scan | Keyed scan | Deep OHLCV / BT | Live trade | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Kraken | ✓ | ✓ | ✓ | ✓ | ✓ | Supported |
| Binance.US | ✓ | ✗ | partial | partial | ✓ | Supported (track + trade) |
| Coinbase Advanced | ✓ | ✗ | partial | partial | ✓ | Supported (track + trade) |
| Gemini | ✓ | ✗ | partial | partial | ✓ | Supported (track + trade) |
| Bitstamp | ✓ | ✗ | partial | partial | ✓ | Supported (track + trade) |
| Crypto.com | ✓ | ✗ | partial | partial | ✓ | Supported (track + trade) |
| Binance | ✓ | ✗ | partial | partial | ✓* | Supported (+ worldwide ack) |
| Bybit | ✓ | ✗ | partial | partial | ✓* | Supported (+ worldwide ack) |
| OKX | ✓ | ✗ | partial | partial | ✓* | Supported (+ worldwide ack) |
| Ethereum (Uniswap) | wallet/LP | thin | ✗ | partial | ✗ | Partial |
| Base (Uniswap) | wallet/LP | thin | ✗ | partial | Base only* | Partial |
| Arbitrum One | wallet/LP | ✗ | ✗ | ✗ | ✗ | Partial |
| Solana DEX | ✓ | ✗ | ✗ | ✗ | ✗ | Partial |
| TradFi (Alpaca etc.) | partial | partial | thin | partial | ✗ | Partial |
| Forex (Alpaca rates) | ✗ | thin | thin | partial | ✗ | Partial |
\*Live trade = dry-run default + per-exchange go-live gate. Worldwide CEX also need `WORLDWIDE_TRADING_ACK=1`. **Partial** = works but thinner than Kraken public research. TradFi BT uses Alpaca IEX when keyed; Forex is rates research only (no FX trade).

Roadmap detail: [`docs/EXCHANGE_ROADMAP.md`](EXCHANGE_ROADMAP.md).
