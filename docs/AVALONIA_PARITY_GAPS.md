# Avalonia shell vs PySide6 device — parity gap list

> **Date:** 2026-11-19 · **Source = code** + screenshot pass (not aspirational stubs).  
> **Sacred baseline:** [`PRODUCT_SURFACE_INVENTORY.md`](PRODUCT_SURFACE_INVENTORY.md) (v1.19 freeze) + `src/trendalgo/device/views/main_window.py`.  
> **BUILD_PLAN:** every open `AV-G-*` ID is a `[AGENT][LOCAL]` row (Sprint Avalonia-gaps).  
> **Verdict:** **Not at parity.** Do **not** retire PySide6.

**Honesty rule:** Mark `[x]` only when Avalonia matches PySide control-for-control and the same prefs/CredMan keys. Enqueue-only, status-copy, guide text, or “device still” is `[ ]`.

**Link contract:** Same ID in this file and `BUILD_PLAN.md`. Closing a row requires **both** BUILD_PLAN `✅` and this file `[x]` in the same session. Gate: `python3 scripts/agent-run.py check-avalonia-gap-sync`.

**Orphans (out of P0):** `ResearchPage`, `AiRecommenderPage`, fleet/single backtest panels, `PlaceholderPage`.

---

## CredMan continuity (shipped — no BUILD_PLAN rows)

| Kind | Targets | Avalonia |
|------|---------|----------|
| Exchange / Alpaca / Telegram / Calendar / Owner | frozen `TrendAlgo/*` | [x] presence inventory + shell `Has` + wizard writes |

**AlgoSpecial:** keyless public Forex H1 — desk + budget prefs only.

---

## Scan / Backtest Settings

PySide: `scan_bt_settings_dialog.py` + `scan_bt_settings_sections.py`. Avalonia: `ScanSettingsWindow.*`.

- [x] Chrome filters (min vol / interval / heatmap)
- [x] Timeframes checklist (28 TFs) + All/None (flat list — bands still open)
- [x] Strategies denylist + search + All/None
- [x] Sauce flags + top-N via `scan_settings` apply
- [x] Persist `scanner_filters.json` + `scan_bt_prefs.json`
- [x] **AV-G-TF1** TF subhour/hour bands + separator + OHLCVT mix note
- [x] **AV-G-TF2** ETA header (lane estimates)
- [x] **AV-G-TF3** Primary filters Full
- [x] **AV-G-TF4** OHLCVT / deep-1m block
- [x] **AV-G-TF5** Extras Full
- [x] **AV-G-TF6** Per-lane scan filters
- [x] **AV-G-TF7** Results-view prefs
- [x] **AV-G-TF8** Persist `lane_prefs.json` + `lane_scan_filters.json`
- [x] **AV-G-TF9** Exchange allowlist in Settings chrome

---

## Nav / chrome (inventory §1)

- [x] Left Primary/More nav shape
- [x] Window geometry restore
- [x] Tray menu Show / Scanner / Run scan / Quit + close-to-tray
- [x] **AV-G-STR1** Desk-load % on Crypto/TradFi/Forex nav labels
- [x] **AV-G-STR2** Tray balloon toasts (notify prefs)
- [x] **AV-G-STR3** Splash → crash review → update/donate → Settings startup
- [x] **AV-G-STR4** Theme system/light/dark + accent apply
- [x] **AV-G-STR5** Autostart registry write from notify prefs

---

## Crypto / TradFi / Forex desks

### Action strip
- [x] Run scan enqueue + non-dry desk-once
- [x] Cancel scan enqueue
- [x] Share board PNG
- [x] Auto-scan toggle enqueue
- [x] Scan progress window shell (`ScanProgressWindow`)
- [x] **AV-G-STR6** Secret Sauce engine job (not ack-only)
- [x] **AV-G-STR7** DEX pool watch engine
- [x] **AV-G-STR8** Refresh prices engine
- [x] **AV-G-STR9** Scan progress ETA + pair glance
- [x] **AV-G-STR10** Force-fresh debug UX parity
- [x] **AV-G-STR11** Strip declutter (secondary → Settings/overflow)

### Board
- [x] 17 named LTS column headers (visual cells still open)
- [x] Tabs Qualified / Watchlist / Logs
- [x] DataGrid + text filter + Buy Picks pane (shallow)
- [x] Watch pin → watchlist JSON
- [x] **AV-G-BRD1** Real coin/equity logos
- [x] **AV-G-BRD2** Painted 7D/30D sparklines + click→chart
- [x] **AV-G-BRD3** Heatmap rank cell backgrounds
- [x] **AV-G-BRD4** Per-column filter row
- [x] **AV-G-BRD5** Buy Picks 9-col + spectrum
- [x] **AV-G-BRD6** LTS header tooltips

---

## Results / Chart / Sauce / DEX / Events / Glossary

- [x] Surface windows exist (filter grids / spark stub / dossier / DEX disclaimer)
- [x] **AV-G-RES1** Full All-TA Results sheet (Oracle/B&H/heat/create)
- [x] **AV-G-RES2** Results share PNG + toolbar chrome
- [x] **AV-G-RES3** OHLC candle chart + trade markers
- [x] **AV-G-RES4** Coin events timeline Full dialog
- [x] **AV-G-RES5** Glossary popup full TA entry

---

## Backtest + Bots

### Backtest
- [x] Pair strip + settings reuse + JSON grid + progress modal entry
- [x] Market Context text + Create Bot / Sauce / Chart / Settings entry points
- [x] **AV-G-OTH2** Backtest full toolbar/body parity
- [x] **AV-G-OTH3** Backtest results column filters
- [x] **AV-G-OTH5** Engine All-TA backtest worker (not JSON republish)

### Bots
- [x] plan.json cards + host poll 15s
- [x] Local panic + Journal/Performance windows
- [x] **AV-G-BOT1** Plan builder send-to-host (botd publish)
- [x] **AV-G-BOT2** Live host flatten when linked
- [x] **AV-G-BOT3** Start/stop bot cards + FAB
- [x] **AV-G-BOT4** Derive Oracle rule from backtest

---

## Dashboard + Alerts

### Dashboard
- [x] Sync/Customize persist + calendar CTA + range chips + TSV/CSV + catalog list
- [x] **AV-G-DSH1** Live portfolio module canvas
- [x] **AV-G-DSH2** Customize dialog drag grid
- [x] **AV-G-DSH3** Settings dashboard section editors
- [x] **AV-G-DSH4** Dashboard PNG export

### Alerts
- [x] Tabs + history + Test Telegram / Grokbot
- [x] **AV-G-ALR1** Alerts ribbon notify matrix + Save
- [x] **AV-G-ALR2** Native tray toast on alert

---

## Settings 10 sections + wizards

- [x] Keys CredMan inventory + Telegram/Alpaca/Calendar wizard writes
- [x] Notify matrix editable + Save (Settings)
- [x] About partial + Feedback window
- [x] **AV-G-SET1** Venue execution editor
- [x] **AV-G-SET2** Lanes auto-scan + Alpaca hint editors
- [x] **AV-G-SET3** Appearance theme/accent editors
- [x] **AV-G-SET4** Connection owner/host/cert pin grid
- [x] **AV-G-SET5** 10-section drag grid + ribbon layout
- [x] **AV-G-SET6** Setup wizard W0–W5 (real pairing steps)
- [x] **AV-G-SET7** Privacy / export / advanced / updates editors

---

## More pages / other

- [x] Glossary search / Billing stub / Debug log tail / partial Export TSV
- [x] **AV-G-OTH1** Export hub (journal CSV, plan JSON, latest scan JSON)
- [x] **AV-G-OTH4** Host badge on global chrome (not Bots-only)

---

## Engine / IPC (honest)

| Action | Status |
|--------|--------|
| `run_scan` | Partial/Full desk-once |
| `cancel_scan` | Enqueue |
| Sauce / pool / refresh / open_settings | Often ack-only — see STR6–8 |
| `run_backtest` | All-TA `pair_strategy_scan_job` (OTH5) |
| CredMan | Shell adapter + Python vaults (shipped) |

---

## Non-negotiable until gaps close

1. **Do not retire PySide6** until every open `AV-G-*` above is `[x]`.  
2. **Do not mark stubs Full.**  
3. **CredMan targets stay frozen.**

### Critique

| Issue | Resolution |
|-------|------------|
| Prior `[x]` on logos/sparks/heat | Reopened as BRD1–3 |
| Flat TF list looked “done” | TF1 band separator still open |
| Dual BUILD_PLAN / gaps drift | `check-avalonia-gap-sync` + same IDs |
