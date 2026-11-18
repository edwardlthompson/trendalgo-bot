# Currency icons (Forex desk)

ISO currency marks for the Forex scanner logo cell (`EUR.png`, `USD.png`, …).

## Resolution

1. `TRENDALGO_CURRENCY_ICONS` (optional override directory)
2. `branding/assets/currencies/` (this folder)

The device seeds missing codes on first Forex paint via glyph marks (`$`, `€`, `£`, …)
using `trendalgo.device.currency_icons.ensure_universe_currency_icons`.

Refresh / regenerate:

```bash
uv run python -c "from trendalgo.device.currency_icons import ensure_universe_currency_icons; print(len(ensure_universe_currency_icons()))"
```
