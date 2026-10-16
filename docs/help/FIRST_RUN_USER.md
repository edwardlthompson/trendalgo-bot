# First run (non-expert)

> You do **not** need exchange API keys to try the Scanner in dry-run.

## Easiest on your PC: TrendAlgo device app (recommended)

The device app is a **native window** on this computer. It does not open a browser.

```powershell
uv sync --extra device
$env:TRENDALGO_DATA_DIR = "$PWD\data"
# Optional: coin logos for the Scanner (or junction branding/assets/coins/from-retired-web-backup)
# $env:TRENDALGO_COIN_ICONS = "C:\Users\edwar\trendalgo-retired-pwa-2026-10-10\examples\web\public\icons\coins"
uv run --extra device python -m trendalgo.device
```

**Start Menu / taskbar (Windows):** after a device build, refresh shortcuts so they no longer point at the retired desktop shell:

```powershell
.\scripts\packaging\install-windows-device.ps1
```

Use `-SkipBuild` if `dist\windows-device\TrendAlgoDevice\TrendAlgoDevice.exe` is already built. If a pinned taskbar icon still fails, unpin it and pin **TrendAlgo** from the Start Menu again.

`TRENDALGO_DATA_DIR` points the app at this repo's `data` folder, where the scan, bots, trades, and portfolio snapshots are saved. Without it, the app reads an empty folder under your user profile (`%USERPROFILE%\.trendalgo\device`), and its pages stay empty. Optional: `TRENDALGO_PORTFOLIO_DB` points at a specific `portfolio.db` (otherwise the app prefers `data\launcher\portfolio.db` when that file exists). Coin logos: set `TRENDALGO_COIN_ICONS`, or use the local junction `branding\assets\coins\from-retired-web-backup` (not committed; see `branding/assets/coins/README.md`).

1. Open **Settings**. For guided setup, press **Open setup wizard**. Each finished step is saved, and **Back** returns to the previous step. Enter your owner ID and host address, then press **Save settings**. The app checks both before it saves anything.
2. In **Settings**, pick a **Theme** (Follow Windows, Light, or Dark) and an **Accent color**. The look changes when you save.
3. **Portfolio** (home after first save) shows net worth, holdings, equity overlays, timeline scrubber, and a holdings heatmap from `portfolio.db`. It does not call the exchange. Live Sync needs a linked host (S-Parity-2).
4. **Opportunity scanner** → set filters if you want, then **Run scan** (public Kraken data, no keys). Cancel stops it. Qualified / Watchlist / Logs tabs, share export, coin logos (when icons are installed), and sparklines match the dense LTS layout. Scan enter/leave history lives on the top-level **Alerts** tab (next to Portfolio).
5. **Backtest** has **One indicator** (candlestick + trade markers) and **Fleet sweep** (pass-1 rankings, Create bot → Plan). It places no orders.
6. **Plan** builds bots (edit in place; stake fixed USD or % equity). Saving keeps the plan on this PC. **Send to host** lands in S-Parity-2.
7. **Bot** shows denser local cards (controls disabled until host). **More** opens Glossary, Export, Research, **AI strategies**, Billing (non-charging), Settings (About), and Debug.

Details: [ADR-0016](../adr/0016-headless-bot-local-device.md). The browser and pywebview launchers were retired on 2026-10-10 (BUILD_PLAN row 23).

## Usability test build (BUILD_PLAN row 20)

Run this checklist with **three first-time users** before you sign off wizard usability. Use the same build and `TRENDALGO_DATA_DIR` as above. Full a11y/visual notes: [`docs/DEVICE_PARITY_LIST.md`](../DEVICE_PARITY_LIST.md) section 13.

| # | Task | Success |
|---|------|---------|
| 1 | Launch the app cold (no prior settings) | Settings opens; user sets owner ID and saves without help |
| 2 | **Open setup wizard** from Settings | User completes **practice mode** through pairing screens using **Back** at least once |
| 3 | **Portfolio** | Net worth or honest empty; timeline/heatmap visible when `portfolio.db` exists |
| 4 | **Scanner** → **Run scan** | Scan finishes or shows a plain error; table or empty state makes sense |
| 5 | **Backtest** → one indicator run on `BTC/USD` | Chart or summary appears; user finds **Cancel** if they start a long run |
| 6 | **Backtest** → **Fleet sweep** (optional) | User sees progress or ETA; **Create bot → Plan** if a row qualifies |
| 7 | **Plan** | Add bot, edit stake (USD or %), save locally |
| 8 | **Bot** | Cards readable; user understands controls need a host |
| 9 | **More** → Glossary, Export, Research, **AI strategies** | Each page loads; AI shows curated presets; suggestions after a scan |
| 10 | Theme + accent in Settings | Change persists after save and restart |

Record the **top three failure points** (where users stall or mis-tap) and file fixes before row 20 sign-off.

## Share with others later: hosted link

When an operator has deployed the dry-run stack ([`docs/DEPLOYMENT.md`](../DEPLOYMENT.md)):

1. Open the HTTPS link they give you.
2. Wait until the status line shows the API is connected.
3. Tap **Scanner** → **Run scan**.

No install on their device. Until that URL exists, prefer the Windows launcher above for your own testing.

## Developers

**Hot reload:**

```powershell
.\scripts\dev-local.ps1
```

→ **http://localhost:5173/**

**Preview (separate UI port, if not using `TRENDALGO_SERVE_WEB`):**

```powershell
.\scripts\preview-local.ps1
```

→ **http://127.0.0.1:4173/**

## Offline / CI scanners

Set `TRENDALGO_MARKET_SOURCE=synthetic` in `.env` for sample markets (no network). **Omit it** for public Kraken OHLCV (still no API keys). The launcher clears synthetic unless you pass `-Synthetic`.

## Coming later

Signed Windows setup.exe / Linux AppImage and a hosted grandma demo URL (ADR-0012). Electron/Tauri is not required for local testing.
