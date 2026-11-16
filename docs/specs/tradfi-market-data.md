# TradFi market data (TF-P5…P11)

## Goal

Alpaca equity OHLCV for research/BT, US RTH session gaps, top-500 universe + disk bar cache, Crypto/TradFi/Forex lane toggles, throttled NASDAQ earnings Events.

## Non-goals

Live equity trading, SIP upgrade, prefetch-all-500 bars, Opportunity desk rewrite.

## DoD

- Keyed path uses Alpaca bars; unkeyed → labeled synthetic.
- RTH/holiday gaps validated (not crypto continuity).
- Registry scan/BT on; live/trading off; support_matrix honest.
- Backtest searchable over universe (→ 500); on-demand cache only.
- Three lane toggles; NASDAQ day-fetch ≤6h cache, ≤20 req/day.

## Tests

Provider keyed/unkeyed; sessions weekend/hole; matrix; lane filter 8 combos; NASDAQ throttle; universe len 500; cache hit skips network.
