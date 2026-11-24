# Product surface inventory (freeze)

> **Purpose:** Durable checklist of every shipped UX/UI surface, function, and engine feature as of **v1.19.0** (`main` @ `9bd0f67`, 2026-11-18). Use this before any Avalonia / dual-runtime cutover so we do not rebuild or silently drop product work.
>
> **Rule:** Avalonia shell must reach **parity** with every **Real** row below before PySide6 device is retired. Engine rows must keep working under Python Research Engine forever. **Orphan / Placeholder** rows stay out of P0 unless resurrected deliberately.
>
> **Do not** treat this file as permission to delete PySide6. It is an inventory + regression gate.

## Snapshot

| Field | Value |
|-------|--------|
| Product version | 1.19.0 |
| Device stack today | PySide6 (`src/trendalgo/device/`) |
| Planned shell | C# Avalonia + permanent Python Research Engine |
| Plan | `.cursor/plans/cross-platform_grids_adr_759c90d5.plan.md` (user plans dir) |
| Profile root | `%USERPROFILE%\.trendalgo\device` (`TRENDALGO_DEVICE_DIR`) |
| String table | `src/trendalgo/device/strings.py` (~885 constants) |
| Inventory date | 2026-11-18 |

### Recent ships that must survive (v1.16–v1.19)

| Version | Must-survive |
|---------|----------------|
| 1.16 | Kraken OHLCVT deep 1m + rolling tip journal |
| 1.17 | Multi-venue parity ladder; quieter Scanner/Backtest; MC + SS-only Oracle leave reasons |
| 1.18 | TradFi + Forex desks, Scan UX, AlgoSpecial H1 |
| 1.19 | AlgoSpecial desk expand: icons, metrics, Bot vs B&H clarity |

---

## 1. Shell chrome (UX)

| Surface | Status | Module / notes |
|---------|--------|----------------|
| Main window title/icon/min size | Real | `views/main_window.py` — TrendAlgo Bot, 480×360 min, ~1100×720 default |
| Geometry restore | Real | `window_geometry.py` → `ui_state.json` |
| Top nav tab bar + More overflow | Real | `nav_layout.py` — adaptive pack |
| Host badge (No host / Linked / events) | Real | Bots/Status poll |
| Status bar (profile + shared DB notes) | Real | |
| System tray (Show / Scanner / Run scan / Quit) | Real | `views/tray_controller.py`; close-to-tray |
| Tray toasts | Real | Balloon + notify prefs |
| Autostart with Windows | Real | `notify_prefs` → Run key |
| Splash → crash review → update/donate → Settings | Real | Startup overlays |
| Theme system/light/dark + accent | Real | Settings appearance |
| Desk-load % on Crypto/TradFi/Forex labels | Real | Nav rewrite during scan paint |

**Primary tabs (0–6):** Dashboard · Alerts · Crypto · TradFi · Forex · Backtest · Bots  
**More (7–11):** Glossary · Export · Billing · Settings · Debug  
**Legacy aliases:** Plan→Bots; Research→Export; AI→Billing (pages not mounted)

---

## 2. Nav destinations (UI pages)

| # | Label | Status | Module | Key actions |
|---|--------|--------|--------|-------------|
| 0 | Dashboard | Real | `views/portfolio_page.py` | Sync All, Customize, demo Top-20, calendar wizard, export PNG/CSV, multi-page grid |
| 1 | Alerts | Real | `views/alerts_page.py` | Notify ribbon; Logs / Entered / Left / Trades |
| 2 | Crypto | Real | `views/scanner_page.py` `lane=crypto` | LTS board, Run/Cancel/Sauce/DEX/refresh/share, Qualified/Watch/Logs, Results, chart |
| 3 | TradFi | Real | same `lane=tradfi` | Alpaca equity desk; Alpaca CTA if keys missing |
| 4 | Forex | Real | same `lane=forex` | Forex desk; autoscan floor ≥90m; AlgoSpecial H1 fallback |
| 5 | Backtest | Real | `views/backtest_page.py` | Pair All-TA, settings, market context, share, create bot, Sauce study |
| 6 | Bots | Real | `views/bots_page.py` | Status + performance + Plan builder + FAB |
| 7 | Glossary | Real | `views/glossary_page.py` | Search `ta-glossary.json` |
| 8 | Export | Real | `views/export_page.py` | Journal CSV / plan JSON / latest scan JSON |
| 9 | Billing | Partial | `views/billing_page.py` | Owner copy; Settle/Referrals **disabled** (ADR-0017) |
| 10 | Settings | Real | `views/settings_page.py` | Ribbon + 10-section drag grid |
| 11 | Debug | Real | `views/debug_page.py` | Tail `device.log` |

### Orphan pages (code exists, not in MainWindow stack)

| Page | Module | Avalonia P0? |
|------|--------|--------------|
| ResearchPage | `views/research_page.py` | No — unless resurrected |
| AiRecommenderPage | `views/ai_recommender_page.py` | No |
| FleetBacktestPanel | `views/fleet_backtest_panel.py` | No |
| SingleBacktestPanel | `views/single_backtest_panel.py` | No |
| PlaceholderPage | `views/placeholder_page.py` | No |

---

## 3. Dashboard modules

**Wired bodies:** `total_worth`, `pl_insights`, `assets`, `portfolio_value`, `cumulative_pnl`, `pl_daily`, `portfolio_vs_market`, `coin_allocation`, `allocation_by_category`, `asset_allocation`, `heatmap`, `top_gainers`, `top_losers`, `inflows_outflows`, `trading_fees_*`, `funding_fees`, `open_orders`, `open_positions`, `events_calendar`, `timeline`, `advanced`

**Catalog stubs (`ExtraModule` thin body):** `market_overview`, `fear_greed`, `watchlist`, `recent_activity`, `accounts_strip`, `drawdown`, `risk_metrics`, `best_worst_days`, `concentration`, `cash_drag`, `income_yield`, `trade_stats`, `exposure_by_venue`, `rebalance_drift`, `goals_progress`, `tax_lots_summary`

Catalog source: `portfolio_module_catalog.py` (and related portfolio views).

---

## 4. Dialogs / wizards

| Surface | Status | Path |
|---------|--------|------|
| Setup wizard (W0–W5) | Real | `wizard/view.py`, `wizard/pages.py` |
| Telegram wizard | Real | `views/telegram_wizard.py` |
| Alpaca wizard | Real | `views/alpaca_wizard.py` |
| Calendar wizard (CMC + Coindar) | Real | `views/calendar_wizard.py` |
| Scan / Backtest Settings | Real | `views/scan_bt_settings_dialog.py` (+ sections) |
| Scan progress | Real | `views/scan_progress_dialog.py` |
| Backtest progress | Real | `views/backtest_scan_dialog.py` |
| Results (All-TA strategy sheet) | Real | `views/scanner_results.py` |
| Scanner chart | Real | `views/scanner_chart_dialog.py` |
| Coin event timeline | Real | `views/coin_event_timeline_dialog.py` |
| DEX pool watch | Real | `views/dex_watch_panel.py` (+ disclaimer) |
| Secret Sauce study | Real | `views/secret_sauce_study.py` |
| Portfolio customize | Real | `views/portfolio_customize_dialog.py` |
| Glossary popup | Real | `views/glossary_popup.py` |
| Feedback | Real | `views/feedback_dialog.py` |
| Crash review | Real | crash review dialog |
| Launch prompt (update/donate) | Real | launch prompt dialog |
| Backtest share | Real | `views/backtest_share_dialog.py` |
| Tray quit confirm | Real | tray controller |

---

## 5. Settings sections

Ribbon: **Save** · **Setup wizard** · **Telegram wizard** · **Alpaca wizard** · Edit layout

| Grid id | Purpose |
|---------|---------|
| connection | Owner ID, host URL, cert SHA-256 pin |
| appearance | Theme, accent, UTC |
| keys | Exchange vault inventory (CredMan) |
| venue | Host vs device execution + disclosure → `execution_venue.json` |
| lanes | Auto-scan Crypto/TradFi/Forex + Alpaca hint |
| dashboard | Module mins / enable list |
| privacy | Crash save toggle |
| data | Help copy (paths) |
| notify | Windows×Telegram matrix, autostart, Grokbot test |
| about | Version, updates, changelog, Venmo/donate, feedback |

---

## 6. Scanner / LTS / Sauce / DEX functions (per lane)

| Function | Status | Notes |
|----------|--------|-------|
| Opportunity board (virtualized model) | Real | `lts_board_model.py`, `scanner_table*` |
| Column sort + per-column filters | Real | |
| Buy Picks pane | Real | `views/buy_picks_pane.py` |
| Board paint / desk-load progress | Real | |
| Tabs: Qualified / Watchlist / Logs | Real | |
| Run scan / Cancel | Real | `scan_job` / `lane_scan_job` + WorkerPool |
| Scan/Backtest Settings (TFs, denylist, OHLCVT, Sauce N, MC, exchanges, vol, heatmaps) | Real | |
| Run Secret Sauce | Real | `opportunity_sauce_job.py` |
| DEX pool watch | Real | Uniswap/Base; `dex_watch_rows.json` |
| Refresh prices | Real | |
| Share board PNG | Real | |
| Results sheet → Create Bot / Sauce Lab / glossary / chart | Real | |
| Candle chart + markers | Real | |
| Coin calendar flags → timeline | Real | |
| Autoscan schedule | Real | Forex ≥90m floor |
| Alerts side-effect (entered/left/trades) | Real | `scanner_alerts.json` + tray/Telegram |
| Lane isolation (no cross-bleed) | Real | Separate DBs / filters |

---

## 7. Backtest / Bots / Alerts functions

| Function | Status | Notes |
|----------|--------|-------|
| Pair All-TA scan | Real | Progress poll ~200ms |
| Market Context pane | Real | |
| Results table + filters | Real | |
| Create bot → Bots hub | Real | |
| Derive Oracle rule | Real | |
| Share strategy PNG | Real | |
| Secret Sauce study entry | Real | |
| Bots: start/stop cards, panic flatten, journal | Real | `status_page`, `bot_cards` |
| Bots: performance table | Real | |
| Plan builder → `plan.json` + send to host | Real | |
| Host poll 15s | Real | |
| Alerts history tabs | Real | |

---

## 8. Engine capabilities (Python — permanent)

| Area | Packages / notes |
|------|------------------|
| All-TA / Oracle / Sauce / Final Boss | `backtest/` (+ `secret_sauce_lab/`) |
| Lanes: crypto / tradfi / forex / dex | Device jobs + `scanner/`, `brokers/`, `dex/`, `venues/` |
| Trading dry-run / live / panic | `trading/`, go-live gate |
| Host botd | `botd/` |
| API host | `api/` (`trendalgo-api`) |
| Market data | `market/` — Kraken OHLCVT, CCXT, Alpaca, AlgoSpecial FX, DEX candles |
| Exchanges | `exchanges/` — 9 CEX + fees/sync |
| TA catalog | `ta/` SIGNAL_REGISTRY |
| Portfolio | `portfolio/` |
| Notifications | Telegram, Grokbot, digest, ntfy/discord/email |
| Billing math | `billing/` Alpha Share (calc-only) |
| Risk / strategies / LTS vendor | `risk/`, `strategies/`, `lts_vendor/`, `lts/` |
| Calendar providers | CoinMarketCal, Coindar, NASDAQ, macro |
| Legal / founder | `docs/legal-desk/`, `scripts/founder_gate.py`, ADR-0020 |

### Venue support (honesty matrix)

- **CEX:** kraken, binanceus, coinbaseadvanced, gemini, bitstamp, cryptocom, binance, bybit, okx  
- **DEX:** ethereum, base, arbitrum, solana  
- **TradFi / Forex:** Alpaca-backed desks (+ AlgoSpecial H1 FX research)

---

## 9. Integrations

| Integration | Role |
|-------------|------|
| Kraken | Full public research + OHLCVT |
| Other CEX (CCXT) | Portfolio + keyed enrich |
| Alpaca | Equity OHLCV + forex rates (paper) |
| AlgoSpecial FX | H1 forex when Alpaca thin |
| DEX plugins | Pool watch / wallet; Base swap gated |
| Telegram | Primary alerts |
| Grok Bot webhook | Opt-in secondary |
| TradingView webhook | Secured ingress (API) |
| Calendar APIs | CMC + Coindar + NASDAQ + macro |
| CoinGecko | Icons / LTS shim (rate-limited) |
| botd host | Device↔VPS pairing |

---

## 10. Persistence contracts (do not break)

### SQLite

`scanner.db`, `scanner_{crypto|tradfi|forex}.db`, `bots.db`, `journal.db`, `ohlcv_prices.db`, `portfolio.db`, `portfolio-demo.db`, `lts_price_cache.db`, icon registry; practice `host.db` / `nonces.db`

### JSON / prefs (selection)

`settings.json`, `plan.json`, `wizard.json`, `ui_state.json`, `notify_prefs.json`, `lane_prefs.json`, `scan_bt_prefs.json`, `scanner_filters.json`, `lane_scan_filters.json`, `lts_scan_rows.json`, `scanner_watchlist.json`, `scanner_alerts.json`, `scanner_alert_state.json`, `settings_layout_prefs.json`, `portfolio_layout_prefs.json`, `execution_venue.json`, `export_prefs.json`, `results_view_prefs.json`, `results_pair_filters.json`, `dialog_geometry.json`, `update_prefs.json`, `crash_prefs.json`, `pending_crash.json`, `dex_watch_rows.json`, sauce/calendar/progress caches

### Windows Credential Manager targets

`TrendAlgo/exchange/{id}/…`, `TrendAlgo/alpaca-*`, `TrendAlgo/telegram-*`, `TrendAlgo/calendar-coinmarketcal`, `TrendAlgo/calendar-coindar`, owner/practice secrets

### Planned dual-runtime addition

Shared **`results.db`** + versioned IPC (Python writes; Avalonia reads). Does **not** replace lane scanner DBs or CredMan.

---

## 11. Packaging / launch

| Path | Role |
|------|------|
| `scripts/packaging/launch-device.ps1` | Source-first `pythonw` (no console) |
| `scripts/packaging/relaunch-device.ps1` | Kill + clear crash + relaunch |
| `scripts/packaging/build-windows-desktop.ps1 -Device` | PyInstaller windowed |
| `scripts/packaging/build-windows-msi.ps1` | MSI |
| `python -m trendalgo.device` | Entry (`--selftest`, `--smoke-backtest`) |

**Invariant:** Day-to-day GUI never shows a console (see `.cursor/rules/device-no-console.mdc`).

---

## 12. Avalonia parity map (P0 must cover)

Expand plan “parity surfaces” beyond a single Scanner page:

| Avalonia P0 surface | Maps from today |
|---------------------|-----------------|
| Dashboard | Portfolio page + wired modules |
| Alerts | Alerts page + notify prefs |
| Crypto desk | Scanner `lane=crypto` |
| TradFi desk | Scanner `lane=tradfi` + Alpaca wizard/CTA |
| Forex desk | Scanner `lane=forex` + AlgoSpecial metrics |
| Backtest | Backtest page |
| Results Workbook | Results dialog + All-TA sheet |
| Sauce / Study | Secret Sauce jobs + study dialog |
| DEX watch | DexWatchDialog |
| Bots hub | Status + Plan + performance |
| Settings | All 10 sections + vaults |
| Glossary / Export / Billing / Debug | More menu pages |
| Wizards | Setup, Telegram, Alpaca, Calendar |
| Tray / autostart / themes | Shell chrome |

**Engine forever (not ported to C#):** All-TA catalog, Sauce Lab, OHLCVT, CCXT adapters, billing math, go-live/founder gates.

---

## 13. Execute gate (before coding Avalonia)

1. `main` pulled and at ≥ inventory version (currently **1.19.0**).  
2. This file reviewed; any new device feature after this date gets a new section row **before** shell work claims “parity.”  
3. ADR-0021 written from the Avalonia plan + this inventory.  
4. PySide6 remains shippable until Avalonia P0 parity checklist on this file is ✅.  
5. No catalog cull; no CredMan namespace rename without migration.

### Critique (inventory process)

| Issue | Resolution |
|-------|------------|
| Silent drop of TradFi/FX/AlgoSpecial | Explicit desks in §2 and §12 |
| Orphans mistaken for product | §2 orphan table = out of P0 |
| Engine rewritten in C# | Forbidden; §8 permanent |
| Prefs/vaults lost | §10 contracts frozen |
| Plan stale vs v1.19 | Parity list expanded; pull verified 2026-11-18 |
