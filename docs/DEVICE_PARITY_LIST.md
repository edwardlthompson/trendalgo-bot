# Device app parity list: PWA design and look

Date: 2026-10-11
Status: Phases 0 to 3 done earlier; **S-Parity-1** (BUILD_PLAN rows 29–40) lands PWA look/feature parity on the device (More nav, Glossary, fleet backtest, candles, portfolio extras, Export/Debug/Research/Billing shells). **S-Parity-2** closes host sync. D4 in `docs/RISK_REGISTER.md` stays open until usability test (BUILD_PLAN row 20) runs.

This compares the native device app (`src/trendalgo/device/`) with the retired PWA and the design sources still in the repo. Each row cites its evidence.

## 1. Sources and method

| Source | Where |
|---|---|
| Device app as it runs today | `src/trendalgo/device/`. Rendered 2026-10-10 at 1100 × 720 with a throwaway profile. Renders are outside the repo in `C:\Users\edwar\AppData\Local\Temp\device-render\` |
| Retired PWA, committed | git HEAD, `examples/web/` (deleted in the working tree by BUILD_PLAN row 23) |
| Retired PWA, latest copy | `C:\Users\edwar\trendalgo-retired-pwa-2026-10-10\` (includes files never committed; see section 9) |
| Golden Path tokens | `design-tokens/design-tokens.json` (tracked). Rules in `docs/DESIGN_GUIDE.md` |
| UX law | `docs/ux-ui-guidelines.md` |
| Brand | `branding/BRANDING.md`, `branding/official-colors.css`, `branding/assets/` |
| Device scope | `docs/adr/0016-headless-bot-local-device.md`, `docs/adr/0017-multi-user-monetization.md` |
| Data | Read-only row counts and symbol checks on `data/*.db`, 2026-10-10 |

Caveat: the PWA homepage snapshot uses mock data (`examples/web/e2e/apiMock.ts`, for example `net_worth_usd: 98_000`). Compare layout and style, not numbers.

## 2. Summary

The bullets describe the device before Phases 0 to 3. Row statuses in sections 4 to 6 are current.

- The device is a plain Qt window: OS palette, default widgets, no logo, no icons, and three style rules (`src/trendalgo/device/theme.py`). No Golden Path token reaches it.
- Much of the emptiness is a data path problem, not missing features. The device reads its own empty profile folder instead of `data/` (D-01). Candle pairs also do not match (D-03). The repo's data holds one scan snapshot, one bot, three trades, and 720 hourly Kraken BTC candles.
- Real feature gaps: no scan on this PC (D-02), no candle download (D-03), and no host sync (section 7). ADR-0016 says heavy work (LTS scans, backtests, plan building) runs on this PC.
- Copy still says "the main app", which no longer exists (D-04).
- The render shows layout defects: 30–60 px gaps between title, subtitle, and content, and labels one row above their fields in Backtests and Plan builder (L-06, L-07).

Priority key:

| Pri | Meaning |
|---|---|
| P0 | Blocks the usability test: pages are empty or misleading, or a feature cannot be reached |
| P1 | Look and layout: the app does not read as TrendAlgo, or has visible defects |
| P2 | Buildable on this PC now; not needed for the test |
| P3 | Needs host sync (ADR-0016); not built |
| P4 | Out of v1, or an owner scope decision (ADR-0017) |

Class: `Gap` = should match the PWA. `By design` = keep the difference. `Blocked` = needs host sync. `Scope` = owner decides.

## 3. Keep (already matches)

| ID | Item | Evidence |
|---|---|---|
| K-01 | Empty states say why and offer one action | `views/widgets.py` `EmptyState`; Status page offers "Go to Plan builder" |
| K-02 | Labels above fields, helper text under them, accessible names | `views/widgets.py` `field()`; UX law: labels above fields |
| K-03 | Problems are text, not color only | `views/widgets.py` `show_problem()` adds the "Problem: " prefix |
| K-04 | No exchange keys on the device | ADR-0016 |
| K-05 | Honest about unsent plans | `views/plan_page.py`: "Saving keeps the plan on this PC. Sending it to the host is not set up yet." |

## 4. Data and flows

| ID | Gap | Device today | Reference | Class | Pri |
|---|---|---|---|---|---|
| D-01 | Device reads an empty folder | `src/trendalgo/device/profile.py` uses `TRENDALGO_DEVICE_DIR` or `~/.trendalgo/device/`, which holds only `device.lock`. The data is in `data/`: `scanner.db` (1 snapshot, 4 opportunities, 4 alerts, 1 watchlist row), `bots.db` (1 bot), `journal.db` (3 trades), `ohlcv_prices.db` (934 candles). Only candles have an override (`TRENDALGO_CANDLES_DB`). | ADR-0016: the device owns its plan and reads host status | Done 2026-10-10 | P0 |
| D-02 | No scan on this PC | `src/trendalgo/device/jobs.py` has no scan job. `views/scanner_page.py` is read-only with one Reload button. | ADR-0016 context: heavy work, including LTS scans, runs on this PC. PWA `scanner/ScannerPanel.ts` has "Run scan", filters, and progress | Done 2026-10-10 (BUILD_PLAN row 26; section 12) | P0 |
| D-03 | Backtests get no candles | Two problems. (a) No candle file in the device profile. `profile.py` points there unless `TRENDALGO_CANDLES_DB` is set, so `jobs.py` raises `NoCandlesError`. (b) Symbol mismatch. The store holds only `BTC` (source `kraken`), with no `BTC/USD` rows. `backtest_page.py` passes the pair as typed, and `OhlcvCache.query` matches `symbol = ?` exactly, so `BTC/USD` returns 0 bars. Also `MIN_BARS = 200` (`jobs.py` line 19), and BTC 4h has only 180 bars. | PWA `backtest/BacktestPanel.ts`: progress bar with ETA and test log | Done 2026-10-10 (device minimum is 100 bars; BTC 4h runs) | P0 |
| D-04 | Copy points to a retired app | `strings.py` lines 21, 24, 28 ("Scans run in the main app", "Run a scan in the main app", "Run a new scan in the main app"). `backtest_model.py` line 56 ("the main app has already saved"). Docstrings in `views/scanner_page.py` line 1 and `profile.py` line 36 say the same. | PWA retired in BUILD_PLAN row 23 | Done 2026-10-10 | P0 |
| D-05 | Setup wizard cannot be reached | No link in the window. `docs/help/FIRST_RUN_USER.md` does not mention it. The frozen build starts only `src\trendalgo\device\__main__.py` (`scripts/packaging/build-windows-desktop.ps1`). The wizard runs separately as `python -m trendalgo.device.wizard`. | ADR-0016 line 10 lists a guided setup wizard. PWA `onboarding/OnboardingChecklist.ts` guides first steps | Done 2026-10-10 | P0 |
| D-06 | Wizard has no Back | `wizard/view.py` has one Continue button. No "Back" anywhere in `src/trendalgo/device`. | UX law: multi-step forms need step position and back | Done 2026-10-10 | P1 |
| D-07 | Status never updates | `views/status_page.py` reads `bots.db` and `journal.db` only | ADR-0016: `GET /api/v1/status`, `GET /api/v1/events` | Blocked | P3 |
| D-08 | Plan is saved locally only | `views/plan_page.py` writes `plan.json`. The message says sending is not set up. | ADR-0016: `PUT /api/v1/plan` | Blocked | P3 |
| D-09 | Backtest result cannot become a bot | No action on results | PWA `backtest/BacktestPanel.ts`: deploy from results | Gap | P2 |
| D-10 | Jargon in Settings | "The owner secret is not stored on this PC yet, so this app cannot sign host requests." (`strings.py` `SETTINGS_NO_SECRET`) | UX law: plain language. Fix with D-04 | Done 2026-10-10 | P1 |

## 5. Look and layout

| ID | Gap | Device today | PWA or repo reference | Class | Pri |
|---|---|---|---|---|---|
| L-01 | No TrendAlgo colors | Only OS palette roles (`theme.py`). On this PC: dark gray window, Windows accent for selection and buttons. | Golden Path (`design-tokens/design-tokens.json`): light primary `#B3263E`, surface `#F5F5FA`, background `#FFFFFF`. Dark primary `#e94560`, surface `#1a1a2e`, background `#12121f` | Done 2026-10-10 | P1 |
| L-02 | No Qt token output | `scripts/sync-design-tokens.py` `write_outputs()` writes `branding/official-colors.css` only. `docs/DESIGN_GUIDE.md` lists web and brand outputs (lines 23–25, 117) and no device output. | Golden Path pipeline | Done 2026-10-10 | P1 |
| L-03 | No theme choice | Follows the OS only | UX law: "follow system with override". PWA `theme.ts` (system, light, dark). Mode select in `components/SettingsPanel.ts` | Done 2026-10-10 | P1 |
| L-04 | No accent presets | Fixed Windows accent | PWA accent presets (`accentPresets`, 5 colors, `theme-meta.json`), applied in `components/SettingsPanel.ts` | Done 2026-10-10 | P2 |
| L-05 | Type scale | Body is Segoe UI 9 pt (12 px at 100% scale). Page title 18 pt semi-bold (`theme.py`). | Golden Path: body 14 px (`bodyMedium`), title 22 px (`titleLarge`) | Done 2026-10-10 | P1 |
| L-06 | Gaps between title, subtitle, and content | Render: 30–60 px gaps on every page (`device-settings.png`, `device-scanner.png`). Cause: with no stretch item, Qt spreads spare height over every label row. Fix: `TailFill` (`views/widgets.py`) gives the spare height to the table, or to one blank tail. | UX law: 4 px base spacing (4, 8, 12, 16, 24, 32, 48, 64) | Done 2026-10-10 | P1 |
| L-07 | Labels one row above their fields | Render (`device-backtests.png`, `device-plan.png`): "Timeframe" and "Indicator" labels sit a row above their combo boxes | UX law: labels above fields | Done 2026-10-10 | P1 |
| L-08 | No panels or radius | Only the empty-state frame has a border and 8 px radius (`theme.py`). Inputs, buttons, and tables are flat Qt defaults. | PWA `.gp-panel`: 1 px outline, radius md, surface background. `.gp-bot-card` is the same (`style.css`) | Done 2026-10-10 | P1 |
| L-09 | No primary action | "Run backtest", "Save plan", "Save settings", and "Reload" look the same | UX law: one primary action per view. PWA `.gp-btn-primary` vs `.gp-btn-secondary` | Done 2026-10-10 | P1 |
| L-10 | No header or status line | Window title only. Status bar shows `Profile folder: ...` (`views/main_window.py`) | PWA `shell/shellChrome.ts` and `AppShell.ts` header: app name, status text, risk badge, bell, settings | Done 2026-10-10 | P1 |
| L-11 | Navigation | Five items in a plain left list. No icons. Long labels such as "Bot status and journal" (`strings.py`) | PWA `shell/MobileNav.ts`: Portfolio, Bot, Scanner, Backtest. More: Glossary, Export, Billing, Settings, Debug | Done 2026-10-10 | P1 |
| L-12 | No mode badge | None | PWA `shell/shellChrome.ts` `createRiskBadge`: Dry-run, Paused, Live, Live (blocked). On the device, "No host linked" could show until P3 | Done 2026-10-10 | P1 |
| L-13 | No logo; name differs | Title "TrendAlgo". No mark on any page. | `branding/assets/*.svg` (tracked). PWA header text "TrendAlgo Bot" (`app.title` in `locales/en.json`). Golden Path `meta.name` is "TrendAlgo". Mark on dark `#1a1a2e` (`branding/BRANDING.md`) | Done 2026-10-10 | P1 |
| L-14 | No app icon | `src/trendalgo/device/app.py` never calls `setWindowIcon`. The `.exe` is built without `--icon`, so it has the PyInstaller default icon. | `branding/assets/app-icon.ico` exists but is untracked (R-02) | Done 2026-10-10 | P1 |
| L-15 | No icons | No `QIcon` in the device package | PWA glyphs ⏸ ▶ ✕ ◎ ☀ ☾ ▲ ▼ and an SVG bell | Partly done 2026-10-10 (nav glyphs and window icon; action glyphs open) | P2 |
| L-16 | No profit or loss color | Numbers in plain text | PWA charts: profit uses the secondary token, loss uses the error token (`design-system/chartTheme.ts`). P/L blocks in `dashboard/BotDashboard.ts` | Done 2026-10-11 | P2 |
| L-17 | Tables are defaults | `QTableWidget` with stretch columns and no row style | PWA dense tables with token colors (`gp-*-table` classes) | Done 2026-10-11 (alternating rows + tokens) | P2 |
| L-18 | No splash | None | PWA boot skeleton (`shell/shellChrome.ts`). `branding/assets/splash-1280x720.png` is untracked (R-02) | Done 2026-10-11 | P2 |

## 6. Features on this PC

| ID | Gap | Device today | PWA reference | Class | Pri |
|---|---|---|---|---|---|
| F-01 | Candlestick chart with trade markers | None. Backtest shows a text summary and a trades table. | PWA `charts/BotChart.ts`: candles, ▲/▼ trade markers, profit and loss regions | Gap | P2 (needs a chart package, O-02) |
| F-02 | Equity curve; portfolio vs top 10 | None | PWA `charts/EquityChart.ts`. Buy-and-hold comparison in `backtest/BacktestPanel.ts` | Partly done 2026-10-11 (equity curve on Portfolio; top-10 compare open) | P2 |
| F-03 | Backtest progress and ETA | "Running" text and a Cancel button (`views/backtest_page.py`, `POLL_MS = 100`) | PWA `backtest/BacktestPanel.ts`: progress bar, phase, ETA, test log | Gap | P2 |
| F-04 | Scanner filters and pinning | Read-only table: Rank, Pair, Gain, Volume score, Entry signal, Trend | PWA `scanner/ScannerPanel.ts` with `scanner/scannerQualOptions.ts`: filters, pin, progress feed | Done 2026-10-11 (Opportunity scanner; owner screenshot). Look pass: BUILD_PLAN row 54 (`parity-scanner-pwa-look`) | P2 (after D-02) |
| F-05 | Sparklines in scanner rows | None | PWA LTS table with sparklines (`examples/web/lts-smoke.png`, backup copy) | Done 2026-10-11 (painter sparklines). Row 54: dual keys `closes_*` / `chart_closes_*` + orange baseline | P2 |
| F-04b | Scanner PWA look (KPI / table density) | Device shell close but plain chips, missing Exchange + 7D/30D gain filters, wrong spark keys, no Results/NEW/pills | Owner screenshot 2026-10-09 Opportunity scanner | Done 2026-10-11 BUILD_PLAN row 54 | P1 |
| F-06 | Plan editing | Add and remove only; no edit in place (`views/plan_page.py`) | PWA `dashboard/botSettingsForm.ts`, `dashboard/BotDetailPage.ts` | Gap | P2 |
| F-07 | Sizing by percent of equity | Fixed USD only: "Stake (USD)" | ADR-0016 sizing policy: fixed USD or percent of equity. PWA `bots.equity.portfolio_pct` | Gap | P2 |
| F-08 | Pair picker | Free text with a `BASE/QUOTE` check only (`fields.py` `check_pair`) | PWA searchable picker, 100+ pairs (`e2e/bot-settings-pickers.spec.ts`) | Gap | P2 |
| F-09 | Indicators and timeframes | 6 live-v1 indicators (`fields.py` `LIVE_V1_INDICATORS`). Timeframes 1h and 4h. | PWA: 100+ strategies and 307 glossary entries. ADR-0016: native strategies stay backtest-only in v1 | Scope | P2 (O-06) |
| F-10 | Strategy glossary | None | PWA `dashboard/TaGlossaryPage.ts`, `dashboard/TaGlossaryCards.ts`, `data/glossaryLinkify.ts`. 307 entries with formulas and see-also links (`public/data/ta-glossary.json`, in HEAD) | Gap | P2 |
| F-11 | Journal view | Plain table from `views/status_page.py`. No P/L color, filter, or chart. | PWA bot detail charts "Actual trades (30D)" and "Simulated backtest (30D)" (`bots.detail.chart_actual`, `bots.detail.chart_simulated` in `locales/en.json`) | Gap | P2 (simulated); P3 (actual) |
| F-12 | Settings: About and version | None | PWA `components/AboutPanel.ts`, `about/updateChecker.ts` | Gap | P2 |
| F-13 | Notifications | None | PWA `notifications/Inbox.ts`; bell in `shell/AppShell.ts` | Gap | P3 |

## 7. Needs host sync (P3)

| ID | Gap | PWA reference | Device today | Class |
|---|---|---|---|---|
| H-01 | Bot cards: state, strategy, pair, equity, realized, unrealized, total P/L | PWA `dashboard/BotDashboard.ts` | Stored-bots table only | Blocked |
| H-02 | Bot controls: start, pause, delete, buy now, sell now | PWA `dashboard/BotDashboard.ts` (`bots.action.*`) | None. ADR-0016 `POST /api/v1/commands` is not built | Blocked |
| H-03 | Live status and event feed | PWA `shell/HealthWidget.ts`, `notifications/Inbox.ts` | None (D-07) | Blocked |
| H-04 | Portfolio overview: net worth, P/L, holdings, exchange accounts | PWA `portfolio/PortfolioPanel.ts`, `portfolio/PortfolioSections.ts`, `portfolio/PortfolioPerformanceChart.ts` | Local read of `portfolio.db` done 2026-10-11 (BUILD_PLAN row 27). Live Sync / keys stay on the host | Local done; live sync Blocked |
| H-05 | Risk and health: drawdown, exposure, status | PWA `shell/HealthWidget.ts`, risk badge | None | Blocked |
| H-06 | Bot limits and templates | PWA `bots/botLimitsMeters.ts`, `bots/botLimitsBanner.ts`, `bots/botTemplatesStore.ts` | None. Decide whether limits live on the host or the device | Scope |
| H-07 | Host connection state | PWA header status text | Only the host address field in Settings | Blocked |
| H-08 | "Actual trades" chart for a live bot | PWA `dashboard/botChartTabs.ts` and `bots.detail.chart_actual` | None | Blocked |

## 8. Out of v1, or owner decisions (P4)

| ID | Item | PWA reference | Basis | Recommendation |
|---|---|---|---|---|
| X-01 | Billing and settlement | `billing/BillingDashboard.ts` | ADR-0017: monetization is not user-visible in v1 | Keep out; owner confirms |
| X-02 | Growth: referrals, leaderboard | `growth/GrowthPanel.ts` | ADR-0017 | Keep out; owner confirms |
| X-03 | Research tools: walk-forward, Monte Carlo, heatmap | `research/ResearchTools.ts`, `research/researchHeatmap.ts`, `research/BacktestVisualizer.ts` | Not in ADR-0016 device scope | Owner decides |
| X-04 | Export hub | `export/ExportHub.ts` | Not in ADR-0016 device scope | Owner decides. A local journal export would be small |
| X-05 | Debug log viewer | `debug/DebugLogViewer.ts` | Developer tool | Dev-only or hidden |
| X-06 | AI recommender | `ai/RecommenderPanel.ts` | Device **More → AI strategies** (curated presets + local rule-based ranks after scan) | Done 2026-10-11 (BUILD_PLAN row 50) |
| X-07 | Portfolio goals | `portfolio/GoalsPanel.ts` | Not in ADR-0016 device scope | Owner decides |
| X-08 | Display currency and update check | `settings/preferences.ts`, `about/updateChecker.ts` | Not in ADR-0016 device scope | Owner decides |
| X-09 | Feedback, crash capture, privacy report, GitHub feedback | `components/FeedbackPanel.ts`, `crash-capture/`, `privacy-report/`, `github-feedback/` (untracked, R-01) | Opt-in telemetry rules (`foss-compliance.mdc`) | Owner decides. Keep opt-in |

## 9. Preservation risks (before any commit of the PWA deletion)

| ID | Item | Where it lives | Risk |
|---|---|---|---|
| R-01 | Untracked PWA source | Backup copy only: `examples/web/public/lts-dashboard/` (LTS UI: `app.js` 194 KB, `styles.css` 58 KB); new files in `examples/web/src/scanner/` (`scanProgress*`, `ltsDisplayFilters*`, `ltsFrameHeight*`, `ltsFramePark.ts`, `ltsCoinAlert.ts`, `scannerHostChrome.ts`, `scannerHostControls.ts`, `scannerQualOptions.ts`, `hydrateDisplayFilters.ts`); `src/bootstrap/`, `src/feedback/`, `src/crash-capture/`, `src/privacy-report/`, `src/github-feedback/`; `components/FeedbackPanel.ts`; `shell/mainViewBootstrap.ts`; `examples/web/scripts/`; `examples/web/lts-smoke.png`; `src/trendalgo/desktop/` (28 files); `src/trendalgo/api/web_static.py`; `scripts/packaging/` launchers | Lost if the backup folder is deleted. The LTS table needs `lts-dashboard/`. |
| R-02 | Untracked brand assets | `branding/assets/app-icon-32.png`, `app-icon-192.png`, `app-icon-512.png`, `app-icon-source.jpg`, `app-icon.ico`, `social-preview.png`, `splash-1280x720.png`, `splash-source.jpg`; `branding/concepts/` (9 images and a README). `branding/BRANDING.md` is modified. | The device icon (L-14) and splash (L-18) depend on these |
| R-03 | Dangling references | `src/trendalgo/scanner/vendor_manifest.json` line 9 points at `examples/web/public/lts-dashboard/`. `src/trendalgo/icons/sync.py` line 18 points at `examples/web/public/icon-registry/`. | The scanner UI and coin-logo sync have no valid path |
| R-04 | Coin logos | 977 files in the backup copy; committed in HEAD under `examples/web/public/icons/coins/` | Recoverable from git. Choose a home before any device logo work |
| R-05 | Mock data in PWA images | `examples/web/e2e/apiMock.ts` | Use the images for layout and style only |

## 10. Owner decisions

Accepted by the owner on 2026-10-10: O-01 option (a), O-03 option (a), O-04 option (a). Owner replied "all" to the four-phase plan (phases 0 to 3, in order). TA-Lib decision (2026-10-10, the owner chose yes): the `device` extra in `pyproject.toml` includes `TA-Lib`, so device backtests use the same signal code as the golden trade lists in `tests/test_lts_vendor`. The CI gap was closed on 2026-10-10 (section 11, item 6).

O-02 decided 2026-10-11: QtCharts (PySide6-Addons) for Portfolio equity; painter sparklines for Scanner rows. Still open: O-05 and O-06. The 4-hour minimum under O-03 (D-03) was closed on 2026-10-10 (section 11, item 2). Phase 3 plan is in section 10a.

## 10a. Phase 3 plan: device look (L-01 to L-14)

Status: done 2026-10-10. Evidence is in the DECISION_LOG entry for the same day.

Scope: L-01 to L-14 (L-03 theme choice and L-04 accent presets included). Glyph icons only in the navigation (part of L-11). Not in this slice: L-15 to L-18 (P2), F-items, and P3 host sync.

Files and changes:

- `design-tokens/design-tokens.json`: add `meta.accentPresets` (the five colors from the retired PWA `theme-meta.json`).
- `scripts/sync-design-tokens.py`: write `src/trendalgo/device/design_tokens.py` (generated: light and dark colors, accent presets, spacing, radius, type sizes, brand mark SVG).
- `src/trendalgo/device/theme_css.py` (pure): mode resolution, colors with accent, stylesheet builder, contrast ratio.
- `src/trendalgo/device/theme.py` (Qt): Fusion style, palette, body font size, stylesheet, active mode.
- `src/trendalgo/device/appearance.py`: read the saved theme and accent from `settings.json`; apply at start; follow the OS color scheme when set to system.
- `src/trendalgo/device/icons.py`: navigation glyphs (one 24-unit stroke family), brand mark pixmap, window icon.
- `src/trendalgo/device/settings_model.py`: `theme` and `accent` fields with defaults.
- `src/trendalgo/device/views/chrome.py` (new): header with brand mark, name, status text, and the "No host linked" badge.
- `src/trendalgo/device/views/main_window.py`: top tab bar with icons; header; icons refresh on palette change.
- `src/trendalgo/device/views/settings_page.py`: Theme and Accent color choices; applied on save.
- `src/trendalgo/device/strings.py`: short navigation labels; header, badge, theme, and accent copy.
- `src/trendalgo/device/app.py` and `wizard/__main__.py`: apply the theme before any window; set the window icon.
- `scripts/packaging/build-windows-desktop.ps1`: `--icon` for the `.exe` and `--add-data` for the window icon.

### Critique

| Issue | Resolution |
|---|---|
| Generated Python module drifts from the tokens | Sync script writes it; a test regenerates it and compares the text. |
| Text contrast falls below WCAG AA in one mode | A test checks each text and background token pair at 4.5:1 or better in both modes. |
| Qt stylesheet and palette disagree | Palette sets defaults; the stylesheet styles named widgets; tests read the window palette and widget properties. |
| A bad theme or accent value blocks bot plan saves | Reading is lenient (defaults for bad appearance values); strict checks apply only to the Settings form. |
| Navigation change breaks tests that read `_nav.currentRow()` | Keep the `_nav` name; update the tests to `currentIndex()`. |
| Icon colors go stale after a theme change | The main window refreshes its icons on palette change; a test covers it. |
| Frozen build has no window icon file | `--add-data` in the build script; the flat mark is the fallback if the file is missing. |
| Theme follows the OS, but the app does not update when the OS changes | Connect the color-scheme change signal and re-apply the saved choice. |
| Larger body font (14 px) clips content at 1100 by 720 | Render check against the PWA snapshot; table pages keep TailFill. |
| Icons are unclear | Each nav item keeps its text label (UX law: labels before icons-only). |
| Product name (O-05) is undecided | Keep "TrendAlgo" unchanged; O-05 stays open. |
| Some PWA tokens do not exist in the token file (error and tertiary containers) | Use only tokens that exist; device has no paused or live state yet. |
| QtSvg may be missing from the frozen build | Importing QtSvg lets PyInstaller collect it; the frozen self-test renders the icons. |

Stop rule: three failed fixes on one item halts that item and escalates (`UX-NNN` entry).

| ID | Decision | Options |
|---|---|---|
| O-01 | Look direction | (a) Match the PWA look: tokens, brand, panels, buttons, header, theme choice, accent presets, icons (recommended). (b) Brand only: tokens, logo, app icon, layout fixes; keep current structure. (c) Keep the native Qt look; fix layout and copy only. |
| O-02 | Charts | (a) PySide6-Addons (QtCharts; LGPL-3.0 like PySide6; candlestick built in). (b) pyqtgraph (MIT; candlestick needs custom drawing). (c) No charts in v1. |
| O-03 | Data path | (a) Quick: point the device at `data/` through env overrides for scanner, bots, journal, and candles. Before that, the device must not switch shared files to WAL on open (`app.py` `prepare_databases`), must confirm that the store classes do not write on open, must map `BTC/USD` to `BTC`, and must handle the 4h bar minimum (180 < 200). (b) Per ADR-0016: the device runs its own LTS scans and keeps its own copies (larger build). |
| O-04 | Untracked PWA and brand files | (a) Commit the brand assets the device needs; archive the rest first (recommended). (b) Archive everything untracked, then commit the deletion. (c) Keep the backup folder as the only copy for now. |
| O-05 | Product name | "TrendAlgo" (device title, Golden Path `meta.name`) or "TrendAlgo Bot" (PWA header, `branding/BRANDING.md`) |
| O-06 | v1 scope for P4 items and the indicator list | Section 8 and F-09 |

## 11. Open items after Phases 0 to 3 (2026-10-10)

Phases 0 to 3 are done. Still open, by priority:

1. D-02 (P0): done 2026-10-10 as BUILD_PLAN row 26 (section 12). Run scan saves to this PC; the Scanner shows the newer of that scan and the bot's saved scan.
2. D-03 (done 2026-10-10): the device minimum is now 100 bars (`MIN_BARS` in `jobs.py`). The longest live warm-up is 50 bars, so BTC 4h (180 bars) runs. Fewer bars can mean fewer trades; revisit the number if 4h results look thin.
3. D-07 and D-08 (P3): status and plan sync need the host API (ADR-0016). Blocked.
4. D-09 (P2), L-15 action glyphs (P2), remaining F-items (not F-04/F-05), H-01 live controls and H-04 live sync, H-02 to H-08, and X-01 to X-09 (sections 6 to 8). L-16 to L-18, F-04, F-05, and local H-04/Portfolio are done 2026-10-11.
5. O-05 (product name) and O-06 (indicator list and scope): owner decisions. O-02 closed (QtCharts + painter sparklines).
6. CI (done 2026-10-10): the python job syncs `--extra dev --extra device`, so TA-Lib and Qt are present for `pytest`. Locally, 54 golden cases failed without TA-Lib. Not run on Linux yet; the next push will show it.
7. Usability test (BUILD_PLAN row 20, HUMAN): run it on the new build with `TRENDALGO_DATA_DIR` set (see `docs/help/FIRST_RUN_USER.md`).

Checked, no action yet: the accent drives borders, focus rings, and the palette's Link role. The amber preset (`#d97706`) is 3.19:1 on white (`theme_css.contrast_ratio`). That meets 3:1 for borders and focus rings, but not 4.5:1 for text. Keep amber off text, or use a darker shade for link text.

## 12. Plan: device scan on this PC (D-02, BUILD_PLAN row 26)

Built 2026-10-10 after the owner approved it ("build now"). ADR-0016 puts heavy work on this PC. The scan uses public Kraken data only, with no exchange keys.

Steps (one vertical slice):

1. Logic: `src/trendalgo/device/scan_model.py` (pure). Builds the scanner settings (defaults in v1) and maps the result to table rows.
2. Job: `scan_job` in `src/trendalgo/device/jobs.py` runs `run_pipeline` (`src/trendalgo/scanner/pipeline.py`) in a pool worker. The snapshot store is in the device profile folder.
3. View: the Scanner page gets a **Run scan** primary button, a progress line from the scan log, and **Cancel** (the same pool and cancel path as Backtests).
4. Tests: `tests/test_device/test_device_scan.py`. Offline only, with `sample=True` or an injected fetcher. Qt view tests run offscreen.
5. Copy in `strings.py`. Results keep the existing read-only table.

Critique:

| Issue | Resolution |
|---|---|
| The scan writes the shared `data/scanner.db`, but the device must not change shared files | The store path is the profile folder. A test checks that the shared file is unchanged after a scan. |
| A scan blocks the window | It runs in the worker pool. The window stays live, and Cancel stops the worker, as Backtests does. |
| Two scans write the same database | One scan at a time, enforced in the page and the pool. The store uses WAL and a busy timeout (D3). |
| Kraken is down or slow | The job returns a plain error. The Scanner keeps the last saved snapshot and says so. |
| Empty, loading, and error states | Empty: "No scan results on this PC yet" with **Run scan**. Loading: the progress line. Error: "Problem:" prefix, not color only. |
| Tests need live data | No test calls Kraken. Tests use `sample=True` or an injected fetcher. |
| The frozen build may miss scanner modules | The build collects them, and `--selftest` gets a `scan` check that runs one offline scan. |
| Copy and look | One primary action, tokens only, text from `strings.py`. |

Out of scope: host sync (D-07), scan filters (F-04), and sparklines (F-05).

Stop rule: three failed fixes on one item halts it and escalates.

**Built (2026-10-10).** Where the build differs from the plan, and why:

- The scan has its own one-worker pool, not the Backtests pool. Cancel on the Scanner therefore never stops a backtest, and a second scan waits in line.
- The status line reads `scan_progress.json` from the profile folder. The worker rewrites it about twice a second, because the scan's progress object lives in the worker process, not the window.
- `scan_job` lives in `scan_job.py`, not `jobs.py`, which is near the 150-line logic limit. `scan_model.py` holds the pure rules. `scan_offline.py` holds the fixed market used by tests and `--selftest`.
- A degraded result is an error, not a saved scan. That covers a failed live fetch and Kraken's fallback pair list, which the pipeline fills with synthetic data. The fallback must not reach the screen.
- The Scanner shows the newer of the bot's saved scan (`data/scanner.db` when `TRENDALGO_DATA_DIR` is set) and this PC's scan, and names the source.
- `--selftest` has a `scan` check. It imports ccxt and runs one offline scan. The frozen build passes it with no build-flag changes.
- The repo conftest sets `TRENDALGO_MARKET_SOURCE=synthetic` for every test. `tests/test_device/conftest.py` removes it, so the scan tests take the live code path with an injected market.
- Live check (2026-10-10): with `TRENDALGO_SCANNER_MAX_PAIRS=10`, one scan qualified 3 of 3 pairs in 20 s and was not degraded. A full universe takes longer. The status line shows the phase and the count while it runs.

## 13. Accessibility and visual smoke (device vs PWA homepage)

Use this checklist before the BUILD_PLAN row 20 usability test. Compare the device at **1100 × 720** with the retired PWA homepage snapshot (mock numbers in `examples/web/e2e/apiMock.ts` or the backup copy). Match **layout, labels, and affordances**, not dollar amounts.

| Check | PWA homepage reference | Device (Qt) | Pass criteria |
|---|---|---|---|
| A-01 App name | Header `app.title` → "TrendAlgo Bot" | `BrandHeader` + window title (`strings.APP_TITLE`) | Same product name visible without opening Settings |
| A-02 Primary nav labels | Portfolio, Bot, Scanner, Backtest | Top tab bar (`NAV_*`: Portfolio, Alerts, Scanner, Backtest, Bot) | Primaries include Alerts (right of Portfolio); Bot remains primary |
| A-03 More overflow | Glossary, Export, Billing, Settings, Debug (+ Research in parity build) | **More** menu (`main_window.MORE_ITEMS`) | Every PWA More item reachable; Research and AI strategies added for local features |
| A-04 Status / risk badge | Header status + risk badge | `chrome.py` badge ("No host linked" until host) | Badge text readable; not color-only (text + outline) |
| A-05 Primary CTA per home view | Portfolio actions, Scanner **Run scan**, Backtest **Run** | One `primaryButton` per page (`theme.py` / widgets) | Primary button visually distinct from secondary on Portfolio, Scanner, Backtest, Plan |
| A-06 Empty states | Panel copy + one action | `EmptyState` (`views/widgets.py`) | Title + body + single button; explains why data is missing |
| A-07 Problem text | Inline errors | `show_problem()` adds "Problem: " prefix | Errors are text, not color alone (K-03) |
| A-08 Form labels | Labels above fields | `field()` helper | Label, control, helper; `setAccessibleName` on nav and tables where set |
| A-09 Keyboard / tab order (Qt) | Browser tab order | Qt focus chain: header → tab bar → **More** → page content → status bar | **Tab** moves forward through focus widgets; **Shift+Tab** reverses. Primary tabs: arrow keys when tab bar focused. **More**: Alt+Down or Enter opens menu; arrows pick item; Enter activates. No trap inside modal-less pages. Document any page where tab skips a control (file a UX row). |
| A-10 Focus visible | Focus ring on controls | Accent-driven focus in `theme.py` stylesheet | Focused field/button shows visible outline (4.5:1 on text where used as link) |
| A-11 Tables | Dense token tables | `read_only_table` + alternating rows | Header row readable; row height fits 14 px body |
| A-11a Screen reader names | `aria-*` in PWA | Qt: `setAccessibleName` on `QTabBar` (`NAV_LABEL`), nav **More**, tables, empty-state buttons | Spot-check with Narrator: nav region and primary button names match visible labels |
| A-12 Charts / sparklines | Color + markers | QtCharts candles; painter sparklines | Profit/loss not conveyed by color alone where numbers exist in adjacent cells |

**How to run (manual, ~15 min):**

1. Launch with sample data: `TRENDALGO_DATA_DIR=%CD%\data` (see `docs/help/FIRST_RUN_USER.md`).
2. Open the PWA homepage screenshot or retired backup render side by side with the device window.
3. Walk A-01 through A-12 on Portfolio → Bot → Scanner → Backtest, then open each **More** page once.
4. Tab from the window title bar through one full page (e.g. Scanner) and note order in the usability test notes.

**Automated guardrails (CI):** contrast tests in `test_device_theme_css.py`; nav/More smoke in `test_device_look.py` and `test_secondary_shells.py`; AI page smoke in `test_ai_recommender_page.py`; scanner look in `test_device_lts_scan.py` / `test_scanner_table.py` / `test_device_scan_page.py` (row 54).

### 13a. Opportunity scanner look (BUILD_PLAN row 54)

Target: owner PWA screenshot (2026-10-09). Device must show Exchange + Min vol + Min gain 7D + Min gain 30D + Uniformity + Scan every + Run scan; KPI cards; Compare/Clear; dense LTS columns including Results; NEW badge; Best BT pill when data exists; sparklines from `closes_*` or `chart_closes_*`. Coin logos via `TRENDALGO_COIN_ICONS` or `branding/assets/coins/from-retired-web-backup` (junction; not committed). Row 54 did not include auto-backtest or column sort/filters (see §14).

### 14. Scanner full parity (S-Scanner-Parity, rows 57–62)

PWA reference: owner screenshot 2026-10-09 + retired `lts-dashboard/`. Device evidence: [`docs/assets/device-scanner-current.png`](assets/device-scanner-current.png) (refreshed after S-Scanner-UX rows 63–65: tabs above title, Watch column, sort chevrons, hourly 7d/30d sparks).

| ID | Gap | Status | BUILD_PLAN |
|----|-----|--------|------------|
| S-01 | Window/taskbar Python logo | Closed 2026-10-12 | `parity-window-icon` ✅ |
| S-02 | Cramped logos; watchlist pin wrong | Closed 2026-10-12 | `parity-scanner-logo-watch` ✅ |
| S-03 | Spark mid-line; no % below high; no chart-dist filter | Closed 2026-10-12 | `parity-scanner-spark-high` ✅ |
| S-04 | No column sort; no per-column dropdowns | Closed 2026-10-12 | `parity-scanner-sort-filters` ✅ |
| S-05 | No auto pass-1 backtest after scan | Closed 2026-10-12 | `parity-scanner-auto-bt` ✅ |
| S-06 | Side-by-side screenshot evidence | Closed 2026-10-12 | `parity-scanner-docs-shot` ✅ |

**Locked:** post-scan **pass-1** backtests on qualified coins only (not full optimize). Sort sorts the coin list then rebuilds widget cells.

### 15. Scanner UX polish (S-Scanner-UX, rows 63–65)

Local device uses **hourly** `closes_1h` for both 7d (168 bars) and 30d (720 bars) sparklines and % below high (so when the high is inside the last 7d, the two % labels match). Watch is its own star column. Sub-tabs sit above the Opportunity scanner title.

| ID | Gap | Status | BUILD_PLAN |
|----|-----|--------|------------|
| U-01 | Tabs below title; no Watch column; no sort chevrons | Closed 2026-10-12 | `parity-scanner-layout-sort` ✅ |
| U-02 | Thin Results list; no TSL hits sheet | Closed 2026-10-12 | `parity-scanner-results-sheet` ✅ |
| U-03 | Screenshot after UX chrome | Closed 2026-10-12 | `parity-scanner-shot` ✅ |

**Locked:** both 7d and 30d charts use hourly `closes_1h` (168 / 720 bars); % below high uses the same window as each spark.
