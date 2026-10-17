# Feature: Modular Dashboard (Portfolio)

## Summary

Device **Dashboard** (nav label; internal id `portfolio`) is a multi-page snap-to-grid of modules: worth, assets, charts, allocation, fees, orders, competition extras, and Events Calendar. Users adjust columns/rows, drag modules with magnetic snap, resize from the bottom-right corner (Android-widget style), export PNG per module or page, and optionally connect CoinMarketCal / Coindar via a setup wizard.

## Spec

- Layout prefs: `portfolio_layout_prefs.json` under the device profile
- Grid: cols 4–32 (default 24), rows 4–96, gap, magnet; **square** cells (`cw == ch`); **Edit layout** shows move handle + BR resize grip and optional grid lines
- Resize: integer cell spans; top-left fixed; catalog / Settings `min_w`/`min_h`/`max_w`/`max_h`; overlap **pushes** neighbors aside (right if free, else down) — does not reject
- Catalog: see `src/trendalgo/device/portfolio_module_catalog.py`; user min overrides in `portfolio_layout_prefs.json` → `module_mins`
- Customize dialog: category sections; checkmarks for modules on any page
- Calendar: official APIs only (CoinMarketCal `x-api-key`, Coindar `access_token`); keys in Credential Manager; no CryptoCraft scrape
- Wizard: `CalendarWizardDialog` — W-CAL-0…4 with Test before Save

## Tests

- `tests/test_device/test_portfolio_layout_prefs.py`
- `tests/test_device/test_calendar_model.py`

## Validation

```bash
python -m pytest tests/test_device/test_portfolio_layout_prefs.py tests/test_device/test_calendar_model.py -q
python3 scripts/agent-run.py watch-agent-gates --once --autofix --scope auto
```
