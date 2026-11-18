# Forex lane (FX-P1…P4)

## Goal

Forex research/BT via Alpaca rates (data-only), liquid universe (~40–80), 24h session rules, Show Forex toggle, keyless macro Events.

## Non-goals

FX live trading (Alpaca cannot trade FX), 500 FX pairs, NASDAQ earnings for FX.

## DoD

- `forex` asset_class + `config/forex_universe.json` + matrix partial.
- Rates → OHLCV when keyed; synthetic offline; weekend gaps OK.
- Device picker when Show Forex on; no order path.
- Macro calendar throttled; Events only when Forex lane shown.

## Tests

Pair normalize; sessions; keyed/unkeyed; lane filter; macro fixture.
