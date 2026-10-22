"""User-facing text for the device app. Visible copy lives here (UX law: externalize strings)."""

APP_TITLE = "TrendAlgo Bot"
NAV_LABEL = "Main navigation"
NAV_PORTFOLIO = "Dashboard"
NAV_ALERTS = "Alerts"
NAV_STATUS = "Bots"
NAV_SCANNER = "Scanner"
NAV_BACKTESTS = "Backtest"
NAV_PLAN = "Plan"
NAV_MORE = "More"
NAV_GLOSSARY = "Glossary"
NAV_EXPORT = "Export"
NAV_BILLING = "Billing"
NAV_SETTINGS = "Settings"
NAV_DEBUG = "Debug"
NAV_RESEARCH = "Research"
NAV_AI = "AI strategies"
GLOSSARY_TITLE = "Glossary"
GLOSSARY_SUBTITLE = "Technical analysis terms used by scanners and backtests on this PC."
GLOSSARY_SEARCH_LABEL = "Search"
GLOSSARY_SEARCH_PLACEHOLDER = "Name, category, or formula"
GLOSSARY_SEARCH_HELP = "Filters the bundled list. Nothing is sent off this PC."
GLOSSARY_COUNT = "{shown} of {total} entries"
GLOSSARY_HEADERS = ("Title", "Category", "ID")
GLOSSARY_NO_MATCH_TITLE = "No matching entries"
GLOSSARY_NO_MATCH_BODY = "Try another word or clear the search box."
GLOSSARY_LOAD_FAILED_TITLE = "Glossary could not load"
GLOSSARY_LOAD_FAILED_BODY = "The bundled glossary file is missing or invalid."
GLOSSARY_DETAIL_FORMULA = "Formula"
GLOSSARY_DETAIL_RELATED = "See also"
GLOSSARY_DETAIL_NONE = "No related entries listed."
EXPORT_TITLE = "Export"
EXPORT_SUBTITLE = "Download plans, journal rows, and scan results from this PC."
EXPORT_FOLDER_FIELD = "Export folder"
EXPORT_FOLDER_LABEL = "Export folder: {path}"
EXPORT_FOLDER_HELP = "Defaults to exports/ under your profile folder. You can pick another folder."
EXPORT_CHOOSE_FOLDER = "Choose folder"
EXPORT_JOURNAL = "Export journal (CSV)"
EXPORT_PLAN = "Export plan (JSON)"
EXPORT_SCAN = "Export latest scan (JSON)"
EXPORT_DONE = "Saved {name} to {path}."
EXPORT_NO_JOURNAL = "No trades in the journal yet."
EXPORT_NO_PLAN = "No plan.json on this PC yet."
EXPORT_NO_SCAN = "No scan results on this PC yet."
RESEARCH_TITLE = "Research"
RESEARCH_SUBTITLE = (
    "Walk-forward and Monte Carlo stay on the host API for now. "
    "This page explains what is missing and exports a local correlation note when portfolio data allows."
)
RESEARCH_WALK_FORWARD_TITLE = "Walk-forward"
RESEARCH_WALK_FORWARD_BODY = (
    "Not on this device yet. Run walk-forward on the host API after the device link is set up."
)
RESEARCH_MONTE_CARLO_TITLE = "Monte Carlo"
RESEARCH_MONTE_CARLO_BODY = (
    "Not on this device yet. Monte Carlo stress tests need the host research endpoints."
)
RESEARCH_CORRELATION_TITLE = "Correlation note"
RESEARCH_CORRELATION_BODY = (
    "Export a JSON note from your saved portfolio holdings on this PC. "
    "Values are placeholders until live price history runs on the host."
)
RESEARCH_CORRELATION_EXPORT = "Export correlation note (JSON)"
RESEARCH_CORRELATION_EMPTY_TITLE = "Not enough holdings"
AI_TITLE = "AI strategies"
AI_SUBTITLE = "Curated presets and rule-based suggestions on this PC. No cloud model runs unless you opt in elsewhere."
AI_HOW_IT_WORKS = (
    "The curated library lists operator-maintained presets (versioned JSON in the repo). "
    "Recommendations rank bundled strategy templates using your latest LTS scan and a simple "
    "risk profile from local portfolio data when available. Run Backtest, edit parameters, "
    "then add bots on Plan. Natural-language drafts and community uploads stay out of v1."
)
AI_CURATED_SECTION = "Curated library"
AI_CURATED_HEADERS = ("Preset", "Strategy", "Version")
AI_CURATED_EMPTY_TITLE = "No curated presets bundled"
AI_CURATED_EMPTY_BODY = "The app ships without a curated library file. Check for an app update."
AI_RECS_SECTION = "Suggestions for you"
AI_RECS_HEADERS = ("Strategy", "Score", "Why")
AI_RECS_NO_REASON = "General fit for your profile."
AI_RECS_EMPTY_TITLE = "No ranked suggestions yet"
AI_RECS_EMPTY_BODY = (
    "Run a scan on Scanner or point the app at sample data (see FIRST_RUN_USER). "
    "Suggestions appear once a scan snapshot exists on this PC."
)
RESEARCH_CORRELATION_EMPTY_BODY = (
    "Need at least two holdings with value in portfolio.db on this PC to export a correlation note."
)
BILLING_TITLE = "Billing"
BILLING_SUBTITLE = "Owner-only view. Charging stays off until legal review finishes (ADR-0017)."
BILLING_OWNER_SECTION = "Performance license"
BILLING_OWNER_BODY = (
    "TrendAlgo stays free for the owner. Statements and on-chain settlement are seams only in v1. "
    "Non-owner billing waits for counsel review (H-006)."
)
BILLING_SETTLEMENT = "Settle on chain"
BILLING_SETTLEMENT_HELP = "Disabled until H-006 and non-owner billing rules ship."
BILLING_GROWTH = "Growth"
BILLING_REFERRALS = "Referrals"
BILLING_REFERRALS_HELP = "Referrals are disabled in v1 (ADR-0017)."
DEBUG_TITLE = "Debug"
DEBUG_SUBTITLE = "Local logs from this app. No data leaves this PC from here."
DEBUG_REFRESH = "Reload log"
DEBUG_PLACEHOLDER = "Log lines appear here when device.log exists under your profile folder."
DEBUG_LINE_COUNT = "Showing {n} lines (last {max} from file)."
DEBUG_EMPTY_TITLE = "No log file yet"
DEBUG_EMPTY_BODY = (
    "When this app writes device.log under your profile folder, the last lines show here."
)

PORTFOLIO_TITLE = "Dashboard"
PORTFOLIO_SUBTITLE = "Net worth and holdings from the last saved snapshot on this PC."
PORTFOLIO_CAPTION = "Last saved snapshot on this PC."
PORTFOLIO_SYNC = "Sync from host"
PORTFOLIO_SYNC_NO_HOST = "Set a host address and pair in the setup wizard before syncing."
PORTFOLIO_SYNC_UNREACHABLE = "The host did not answer. Check the address and try again."
PORTFOLIO_SYNC_REFUSED = "The host refused the sync call. Check the owner secret and ID."
PORTFOLIO_SYNC_EMPTY = "The host is linked, but it has not published a portfolio snapshot yet."
PORTFOLIO_AS_OF = "As of {when}."
PORTFOLIO_TAB_OVERVIEW = "Overview"
PORTFOLIO_TAB_HOLDINGS = "Holdings"
PORTFOLIO_TAB_ANALYTICS = "Analytics"
PORTFOLIO_TAB_TOOLS = "Tools"
PORTFOLIO_SHARE = "Share PNG"
PORTFOLIO_DEMO_BADGE = "Demo"
PORTFOLIO_LOAD_DEMO = "Load Top-20 demo"
PORTFOLIO_EXIT_DEMO = "Exit demo"
PORTFOLIO_DEMO_CAPTION = (
    "Top-20 demo portfolio — Sync from host or Exit demo to return to your balances."
)
PORTFOLIO_SHARE_DONE = "Saved screenshot {name} under {path}."
PORTFOLIO_SHARE_TIP = "Save a PNG of the active Dashboard page or selected module."
PORTFOLIO_SYNC_ALL = "Sync All"
PORTFOLIO_CUSTOMIZE = "Customize"
PORTFOLIO_EDIT_LAYOUT = "Edit layout"
PORTFOLIO_RESIZE_MODULE = "Drag corner to resize"
PORTFOLIO_EXPORT_PAGE = "Export page PNG"
PORTFOLIO_EXPORT_MODULE = "Export PNG"
PORTFOLIO_GRID_COLS = "Columns"
PORTFOLIO_GRID_ROWS = "Rows"
PORTFOLIO_SHOW_GRID = "Show grid"
PORTFOLIO_ADD_PAGE = "Add page"
PORTFOLIO_RENAME_PAGE = "Rename page"
PORTFOLIO_DELETE_PAGE = "Delete page"
PORTFOLIO_RESET_LAYOUT = "Reset layout"
PORTFOLIO_REMOVE_MODULE = "Remove"
PORTFOLIO_MODULE_EMPTY = "Nothing so far"
PORTFOLIO_MODULE_EMPTY_HINT = "Sync from the host or load the Top-20 demo to get started."
PORTFOLIO_CALENDAR_SETUP = "Set up calendar APIs"
PORTFOLIO_CALENDAR_CONNECTED = "Calendar connected"
PORTFOLIO_CHIP_24H = "24H"
PORTFOLIO_CHIP_1W = "1W"
PORTFOLIO_CHIP_1M = "1M"
PORTFOLIO_CHIP_3M = "3M"
PORTFOLIO_CHIP_6M = "6M"
PORTFOLIO_CHIP_1Y = "1Y"
PORTFOLIO_CHIP_YTD = "YTD"
PORTFOLIO_CHIP_ALL = "ALL"
PORTFOLIO_QUOTE_USD = "USD"
PORTFOLIO_ASSETS_SORT_NAME = "Name"
PORTFOLIO_ASSETS_SORT_PRICE = "Price"
PORTFOLIO_ASSETS_SORT_HOLDINGS = "Holdings"
PORTFOLIO_ASSETS_SORT_24H = "24h"
PORTFOLIO_ASSETS_SORT_AVG_BUY = "Avg Buy"
PORTFOLIO_ASSETS_SORT_PROFIT = "Profit / Loss"
PORTFOLIO_ASSETS_SORT_ALLOC = "Allocation"
PORTFOLIO_HEADERS_RICH = (
    "Name",
    "Amount",
    "24h Change",
    "Price",
    "Total",
    "Avg Buy",
    "P/L",
)
PORTFOLIO_DEMO_TIP = "Preview a sample Top-20 coin portfolio with a synthetic equity curve."
PORTFOLIO_ALLOCATION = "Allocation"
PORTFOLIO_GAINERS = "Top gainers"
PORTFOLIO_LOSERS = "Top losers"
PORTFOLIO_VS_BENCHMARKS = "Vs Top 10 / buy & hold (chart on Overview)."
PORTFOLIO_EMPTY_TITLE = "No saved portfolio on this PC"
PORTFOLIO_EMPTY_BODY = (
    "Point this app at a data folder that already has portfolio.db, or sync from the host later."
)
PORTFOLIO_NO_HISTORY = "Not enough history for a chart yet."
PORTFOLIO_NET_WORTH = "Net worth"
PORTFOLIO_DAILY = "Daily P/L"
PORTFOLIO_REALIZED = "Realized"
PORTFOLIO_REALIZED_UNAVAILABLE = "Unavailable"
PORTFOLIO_UNREALIZED = "Unrealized"
PORTFOLIO_NFT_UNTRACKED = "NFTs not valued yet"
STATUS_PANIC = "Panic — halt buys & flatten"
STATUS_PANIC_TIP = "Halts new buys on all venues, pauses bots, and requests flatten."
STATUS_LIGHTS = "Vault · Sync · Live"
STATUS_LIGHTS_FMT = "Vault: {vault} · Sync: {sync} · Live: {live}"
SETTINGS_KEYS = "Exchange API keys"
SETTINGS_KEYS_HELP = (
    "Keys stay in Windows Credential Manager on this PC. They are not part of Save settings. "
    "Start with query-only. Live trading still needs a separate go-live approval."
)
SETTINGS_KEYS_SAVED = "Saved keys"
SETTINGS_KEYS_EMPTY = "No exchange keys saved yet. Add one below."
SETTINGS_KEYS_COL_EXCHANGE = "Exchange"
SETTINGS_KEYS_COL_SCOPE = "Use"
SETTINGS_KEYS_COL_STATE = "Status"
SETTINGS_KEYS_UPDATE = "Update"
SETTINGS_KEYS_ADD = "Add or rotate key"
SETTINGS_KEYS_EXCHANGE = "Exchange"
SETTINGS_KEYS_SCOPE = "Key use"
SETTINGS_KEYS_SCOPE_HELP = (
    "Query can only read balances. Trade can place orders when go-live is approved."
)
SETTINGS_KEYS_SCOPE_QUERY = "Query (read-only)"
SETTINGS_KEYS_SCOPE_TRADE = "Trade + query"
SETTINGS_KEYS_PUBLIC = "Public API key"
SETTINGS_KEYS_PUBLIC_HELP = "The public key or API key ID from your exchange."
SETTINGS_KEYS_PUBLIC_PLACEHOLDER = "Paste public API key"
SETTINGS_KEYS_PRIVATE = "Private API secret"
SETTINGS_KEYS_PRIVATE_HELP = "The private secret. Never share it or paste it into chat."
SETTINGS_KEYS_PRIVATE_PLACEHOLDER = "Paste private API secret"
SETTINGS_KEYS_TEST = "Test connection"
SETTINGS_KEYS_SAVE = "Save key"
SETTINGS_KEYS_DELETE = "Remove key"
SETTINGS_KEYS_DELETE_CONFIRM = "Remove the saved API key for {brand} from this PC?"
SETTINGS_KEYS_OK_TITLE = "Keys work"
SETTINGS_KEYS_NONE = "No key saved for this exchange"
SETTINGS_KEYS_REQUIRED = "Public and private keys are both required"
SETTINGS_KEYS_SAVE_FIRST = "Save a key first"
SETTINGS_KEYS_VERIFIED = "verified"
SETTINGS_KEYS_UNVERIFIED = "saved (not verified)"
SETTINGS_KEYS_STATUS = "{scope} · {state}"
SETTINGS_DATA_HELP = (
    "Export plans, journal CSV, and scan snapshots from the Export page. "
    "Settings stay on this PC in settings.json."
)
SETTINGS_VENUE = "Trading venue"
SETTINGS_VENUE_HOST = "Host (recommended)"
SETTINGS_VENUE_DEVICE = "This PC (opt-in)"
SETTINGS_VENUE_DISCLOSURE = (
    "Device-local live can miss entries or exits when this PC sleeps, reboots, "
    "loses power, or drops its ISP. A always-on host is recommended."
)
SETTINGS_VENUE_ACK = "I understand the risks of device-local live trading"
PORTFOLIO_TOTAL_PL = "Total P/L"
PORTFOLIO_HEALTH = "Health"
PORTFOLIO_DRAWDOWN = "Max drawdown"
PORTFOLIO_HOLDINGS = "Holdings"
PORTFOLIO_HEADERS = ("Asset", "Alloc %", "Quantity", "Price", "Value", "Cost", "Unrealized", "Tag")
PORTFOLIO_HIDE_DUST = "Hide dust (<$1)"
PORTFOLIO_EXPORT_CSV = "Export holdings CSV"
PORTFOLIO_RANGE = "Chart range"
PORTFOLIO_TIMELINE = "Snapshot date"
PORTFOLIO_ONE_SNAPSHOT = "Only one saved snapshot so far — timeline picks appear after more syncs."
PORTFOLIO_HEATMAP = "Holdings returns"
PORTFOLIO_HEATMAP_EMPTY = "No holdings to map."
PORTFOLIO_CHART_PORTFOLIO = "Portfolio"
PORTFOLIO_CHART_TOP10 = "Top 10 index"
PORTFOLIO_CHART_BUY_HOLD = "BTC buy & hold"
PORTFOLIO_SYNC_APPLIED = "Host portfolio saved on this PC."
PORTFOLIO_ACCOUNTS = "Exchange accounts"
PORTFOLIO_ACCOUNT_HEADERS = ("Exchange", "Label")
PORTFOLIO_ACCOUNTS_EMPTY = "No accounts"
PORTFOLIO_ACCOUNTS_EMPTY_BODY = "Accounts appear after a host sync or local snapshot."
PORTFOLIO_REBALANCE = "Rebalance suggestions"
PORTFOLIO_REBALANCE_HEADERS = ("Asset", "Action", "Delta %", "Delta $")
PORTFOLIO_REBALANCE_EMPTY = "No rebalance targets"
PORTFOLIO_REBALANCE_EMPTY_BODY = (
    "Set allocation targets on the host or in portfolio.db to see suggestions."
)
PORTFOLIO_GOALS = "Goals"
PORTFOLIO_GOALS_NONE = "No performance goal saved yet."
PORTFOLIO_GOALS_PROGRESS = "{label}: {pct}% toward target."
PORTFOLIO_ARB = "Arbitrage watch"
PORTFOLIO_ARB_HEADERS = ("Pair", "Buy", "Sell", "Spread")
PORTFOLIO_ARB_EMPTY = "No spreads"
PORTFOLIO_ARB_EMPTY_BODY = "Dry-run venue quotes appear here when available."
HEADER_STATUS = "Running on this PC"
BADGE_NO_HOST = "No host linked"
BADGE_HOST_LINKED = "Host linked"
BADGE_HOST_EVENTS = "Host linked · {count} event(s)"
PROFILE_NOTE = "Profile folder: {path}"
DATA_NOTE = "Data folder, read only here: {path}"
PROBLEM_PREFIX = "Problem: "
RELOAD = "Reload"
CANCEL = "Cancel"
WAL_NOTICE = "{name} could not switch to safe-write mode. It stays as it is for now."
PROFILE_FOLDER_FAILED = (
    "The profile folder cannot be created: {reason}. Check the folder path, then start again."
)
SAVE_FAILED = "Could not save: {reason}. The file on disk was not changed."

SCANNER_TITLE = "Opportunity scanner"
SCANNER_SUBTITLE = (
    "Scan the exchanges you select (API keys required). Each venue gets its own rows; "
    "volume is that venue’s notional, not CoinMarketCap."
)
SCANNER_EMPTY_TITLE = "No scan results on this PC yet"
SCANNER_EMPTY_BODY = (
    "Add exchange API keys in Settings, check venues in the Exchange list, then press Run scan."
)
SCANNER_EXCHANGES_NEED_KEYS = "Add API keys…"
SCANNER_EXCHANGES_NONE = "No exchanges"
SCANNER_EXCHANGES_ALL = "All keyed"
SCANNER_EXCHANGES_N = "{n} exchanges"
SCANNER_NO_EXCHANGES = (
    "No exchanges selected (or no API keys saved). Open Settings → Exchange API keys, "
    "then check venues here."
)
SETTINGS_KEYS_RATE = "API calls this minute: {used} / {max}"
SETTINGS_KEYS_RATE_EMPTY = "API calls this minute: —"
SETTINGS_LAYOUT_EDIT = "Arrange modules"
SETTINGS_LAYOUT_EDIT_TIP = "Drag and resize Settings modules like the Dashboard."
SCAN_BT_SETTINGS = "Settings"
SCAN_BT_SETTINGS_TIP = "Timeframes, strategies, and scan-time estimate"
SCAN_BT_SETTINGS_TITLE = "Scan & backtest settings"
SCAN_BT_SETTINGS_SAVED = "Scan settings saved."
SCAN_BT_TF_TITLE = "Timeframes"
SCAN_BT_TF_SUBHOUR = "Sub-hour"
SCAN_BT_TF_HOURS = "Hours (1h–24h)"
SCAN_BT_TA_TITLE = "Strategies (All TA)"
SCAN_BT_TA_SEARCH = "Search strategies…"
SCAN_BT_SELECT_ALL = "All"
SCAN_BT_SELECT_NONE = "None"
SCAN_BT_NO_TFS = "Select at least one timeframe in Settings."
SCAN_BT_NO_STRATEGIES = "Enable at least one strategy in Settings."
SCANNER_NONE_TITLE = "The last scan qualified no pairs"
SCANNER_NONE_BODY = "Nothing passed the filters in that scan. Press Run scan to check again."
SCANNER_FILTER_NONE_TITLE = "No coins match these column filters"
SCANNER_FILTER_NONE_BODY = "The table is still here — set Min gain 7D / 30D back to All (0), or clear the other column filters."
SCANNER_FILTERS_SAVED = "Filters saved. Press Run scan to refresh results."
SCANNER_FILTER_NONE_STATUS = (
    "No coins match the column filters. Set the 7D% / 30D% filters back to All to show rows again."
)
SCANNER_CAPTION = "Scan {scan_id} as of {as_of}."
SCANNER_DEGRADED = " Some data was missing, so read this scan with care."
SCANNER_FROM_PC = "Scanned on this PC."
SCANNER_FROM_BOT = "Saved by the bot."
SCANNER_HEADERS = ("Rank", "Pair", "Gain", "Volume score", "Entry signal", "Trend")
SCANNER_LTS_HEADERS = (
    "Watch",
    "Logo",
    "Name",
    "7D%",
    "7D",
    "30D%",
    "30D",
    "Best BT %",
    "Bot vs B&H",
    "Uniformity",
    "Health",
    "HV 7D",
    "Max DD",
    "Vol Δ%",
    "Exchange",
    "24H Vol",
    "Backtest",
)
# Match retired LTS dashboard column titles (hover help for new users).
SCANNER_LTS_HEADER_TIPS = (
    "Pin this pair to the Watchlist",
    "Coin logo",
    "Asset name (opens listing) with ticker",
    "Seven-day percent gain from snapshot",
    "Seven-day hourly sparkline; % below window high. Orange line is last close.",
    "Thirty-day percent gain from snapshot",
    "Thirty-day hourly sparkline; % below window high. Orange line is last close.",
    "Highest backtest net percent and winning trailing stop (TSL) when not buy and hold",
    "Edge of the best strategy over buy and hold net % (when strategy beats B&H)",
    "OHLCV uniformity score",
    "Composite health score",
    "Annualized historical volatility from about 7d of hourly closes",
    "Peak-to-trough drawdown over about 30d of hourly closes",
    "Volume acceleration vs baseline window",
    "Listing venue for this row",
    "Approximate 24h USD volume on Kraken spot for this base (all quotes; not CoinMarketCap global)",
    "Open optimizer results when a pass-1 backtest is saved for this pair",
)
SCANNER_COLOR_RANKS = "Color ranks"
BACKTEST_PERFECT_ONLY = "Perfect Strategies"
BACKTEST_PERFECT_HELP = (
    "Show only strategies with a 100% win rate and zero trailing-stop hits "
    "(plus buy & hold). Not the same as Oracle max (perfect trough→peak swings)."
)
BACKTEST_ORACLE_LABEL = "Oracle max  ← perfect trough→peak"
BACKTEST_DERIVE_RULE = "Derive rule from oracle"
BACKTEST_DERIVE_RULE_HELP = (
    "Mine a local GEN_ORACLE rule from oracle swings vs strategy misses "
    "(requires a prior All-TA run with Oracle max)."
)
BACKTEST_DERIVE_EMPTY = "Run All-TA first so Oracle max and strategy rows exist."
BACKTEST_DERIVE_NONE = "No composite rule found from the current oracle gap."
SECRET_SAUCE_LABEL = "Secret Sauce Lab"
SECRET_SAUCE_TA_LABEL = "Secret Sauce TA"
SECRET_SAUCE_PARAMS_STUB = "entry+exit · study"
SECRET_SAUCE_STUDY_TITLE = "{name} — {symbol}"
SECRET_SAUCE_STUDY_EMPTY = (
    "No heartbeat dossier on this row. Re-run All-TA / Backtest to refresh Secret Sauce."
)
SECRET_SAUCE_STUDY_META = (
    "Pair {pair} · TF {tf} · train coverage {train:.0f}% · holdout {hold:.0f}%"
)
SECRET_SAUCE_STUDY_NETS = (
    "Replay Net % — {name} {sauce:.2f}% · B&H {bh:.2f}% · Oracle ceiling {oracle:.2f}%"
)
SECRET_SAUCE_REGIME = (
    "Regime — {structural} · vol {volatility} · dir {direction}"
    "{squeeze} · confidence {confidence:.0%}"
)
SECRET_SAUCE_REGIME_VOTES = "Votes — ADX {adx} · ER {er} · CHOP {chop} · ribbon {ribbon}"
SECRET_SAUCE_PENDING = "Secret Sauce Lab is still cooking…"
SCAN_PHASE_CATALOG = "Catalog TA (parallel)…"
SCAN_PHASE_SAUCE_COINCIDENCE = "Secret Sauce TA — Oracle×catalog coincidence…"
SCAN_PHASE_SAUCE_REFINE = "Secret Sauce Lab refine (~12s)…"
SCAN_PHASE_SAUCE_MERGE = "Secret Sauce Lab merge…"
SECRET_SAUCE_FORMULA = "Formula (Enter + Exit — same rhyme every trade)"
SECRET_SAUCE_ENTER = "Enter"
SECRET_SAUCE_EXIT = "Exit"
SECRET_SAUCE_COVERAGE = "Oracle swing coverage under this formula"
SECRET_SAUCE_RESIDUAL = (
    "Residuals — missed entries {n_entry} · missed exits {n_exit}{gap}{features}"
)
SECRET_SAUCE_COL_SWING = "#"
SECRET_SAUCE_COL_ENTRY = "Entry bar"
SECRET_SAUCE_COL_EXIT = "Exit bar"
SECRET_SAUCE_COL_FIRED = "Entry fired?"
SECRET_SAUCE_COL_EXIT_FIRED = "Exit fired?"
SECRET_SAUCE_YES = "Yes"
SECRET_SAUCE_NO = "No"
SECRET_SAUCE_COPY = "Copy formula"
SECRET_SAUCE_CREATE_BOT = "Create bot from Secret Sauce"
ALERTS_TAB_LOGS = "Logs"
ALERTS_TAB_ENTERED = "Entered"
ALERTS_TAB_LEFT = "Left"
ALERTS_TAB_TRADES = "Trades"
ALERTS_RIBBON_HELP = (
    "Toggle notifies for Entered, Left, and Trades (Windows toast + Telegram together). "
    "Preview shows the live wording; Test sends a real sample."
)
ALERTS_PREVIEW_WINDOWS = "Windows toast"
ALERTS_PREVIEW_TELEGRAM = "Telegram message"
ALERTS_TEST_WINDOWS = "Test Windows"
ALERTS_TEST_TELEGRAM = "Test Telegram"
ALERTS_TEST_OK = "Test sent."
ALERTS_TEST_TG_NEED = "Set up Telegram in Settings first (token + chat id)."
ALERTS_TEST_TG_FAIL = "Telegram test failed. Check token, chat id, and network."
ALERTS_NOTIFY_ON = "On"
ALERTS_NOTIFY_OFF = "Off"
SCANNER_FILTER_SIGNALS = "Signals"
SCANNER_SIGNALS_3COMMAS = "3Commas"
SCANNER_SIGNALS_ALL_TA = "All TA"
SCANNER_TAB_QUALIFIED = "Qualified"
SCANNER_TAB_WATCH = "Watchlist"
SCANNER_TAB_LOGS = "Logs"
SCANNER_TAB_ALERTS = "Alerts"
SCANNER_FILTER_EXCHANGE = "Exchange"
SCANNER_FILTER_VOL = "Min vol"
SCANNER_FILTER_GAIN = "Min gain %"
SCANNER_FILTER_GAIN_7D = "Min gain 7D"
SCANNER_FILTER_GAIN_30D = "Min gain 30D"
SCANNER_FILTER_UNIT = "Uniformity"
SCANNER_FILTER_EVERY = "Scan every"
SCANNER_FILTER_CHART_7D = "7d chart"
SCANNER_FILTER_CHART_30D = "30d chart"
SCANNER_FILTER_HEALTH = "Health"
SCANNER_FILTER_UNIT_MIN = "Unit ≥"
SCANNER_FILTER_VOL_ACCEL = "Vol Δ"
SCANNER_FILTER_VOL24 = "24h vol"
SCANNER_CHIP_QUALIFIED = "Qualified coins"
SCANNER_CHIP_COINBASE = "Coinbase coins"
SCANNER_CHIP_KRAKEN = "Kraken coins"
SCANNER_CHIP_COUNT = "{n}"
SCANNER_SHARE = "Share"
SCANNER_SHARE_TIP = "Export the filtered scanner list as a PNG image."
SCANNER_SHARE_DIALOG = "Export scanner results"
SCANNER_SHARE_FILTER = "PNG image (*.png)"
SCANNER_SHARE_DONE = "Saved {name} under {path}."
SCANNER_SHARE_NEED_ROWS = "Run a scan and keep at least one row visible before sharing."
SCANNER_RESULTS_SHARE_TIP = "Export this strategy sheet as a PNG image."
SCANNER_RESULTS = "Results"
SCANNER_RESULTS_TITLE = "Backtest results — {symbol}"
SCANNER_RESULTS_EMPTY = "No backtest sweep is saved for this pair yet."
SCANNER_CREATE_BOT = "Create Bot"
SCANNER_CREATE_BOT_DONE = "Added {name} on Plan."
SCANNER_CREATE_BOT_PARTIAL = "Opened Plan — pick a live indicator to finish."
SCANNER_GLOSSARY_MISS_TITLE = "No glossary entry"
SCANNER_GLOSSARY_MISS_BODY = "No bundled glossary item matched {name}."
SCANNER_CHART_TITLE = "Price chart — {symbol}"
SCANNER_CHART_SHOW_TRADES = "Show trade overlays"
SCANNER_CHART_EMPTY = "No price series is available for this pair yet."
SCANNER_CHART_NO_STRATEGIES = "No top strategies to overlay yet."
SCANNER_CHART_NET_MISMATCH = (
    "{indicator}: overlay net {overlay:+.1f}% vs Results {results:+.1f}% "
    "({trades} trades, {tsl_n} TSL)."
)
SCANNER_NEW_BADGE = "NEW"
SCANNER_ALERTS_TITLE = "No alerts on this PC"
SCANNER_ALERTS_BODY = "Alerts from a scan show here when the scanner records them."
SCAN_RUN = "Run scan"
SCAN_STARTING = "Starting. The first scan loads the pair list, which can take a minute."
SCAN_DONE = "Done. The new scan is saved on this PC."
SCAN_CANCELLED = "Cancelled. The last saved scan is still shown."
SCAN_UNAVAILABLE = (
    "Kraken data was not available, so no scan was saved. The last saved scan is still shown."
)
SCAN_FAILED = "The scan did not finish. Check the connection, then run it again."

BACKTEST_TITLE = "Backtests"
BACKTEST_SUBTITLE = (
    "Pick a pair and press Scan. TrendAlgo runs the same All-TA sweep as the Opportunity "
    "scanner across each timeframe, then lists every strategy (and buy & hold) by Net %. "
    "This page places no orders."
)
BACKTEST_TAB_SINGLE = "One indicator"
BACKTEST_TAB_FLEET = "Fleet sweep"
BACKTEST_PAIR = "Pair"
BACKTEST_PAIR_HELP = "Use BASE/QUOTE, for example BTC/USD."
PAIR_PICKER_PLACEHOLDER = "BTC/USD"
BACKTEST_TIMEFRAME = "Timeframe"
BACKTEST_INDICATOR = "Indicator"
BACKTEST_STOP = "Trailing stop (%)"
BACKTEST_STOP_HELP = "Enter 0 to turn the trailing stop off. Otherwise enter 1 to 20."
BACKTEST_RUN = "Scan"
BACKTEST_RUNNING = "Scanning All-TA strategies…"
BACKTEST_CANCELLED = "Cancelled. No result was kept."
BACKTEST_DONE = "Done. Results are sorted by Net % (highest first)."
BACKTEST_FAILED = "The scan did not finish. Check the pair and connection, then try again."
BACKTEST_EMPTY_TITLE = "No pair scan yet"
BACKTEST_EMPTY_BODY = (
    "Choose a pair, then press Scan to test every TA strategy over each timeframe."
)
BACKTEST_NO_CANDLES_TITLE = "No price data for this pair"
BACKTEST_NO_CANDLES_BODY = (
    "The All-TA loader found no candles for this pair. Try another pair or wait for cache data."
)
BACKTEST_NO_TRADES_TITLE = "No trades in this run"
BACKTEST_NO_TRADES_BODY = "This indicator made no trades on these candles. Try another timeframe."
BACKTEST_CHART_TITLE = "Price chart"
BACKTEST_CHART_EMPTY = "Not enough candle history to draw a chart."
BACKTEST_CHART_ENTRY = "Entry"
BACKTEST_CHART_EXIT = "Exit"
BACKTEST_TRADES_TITLE = "Last trades"
BACKTEST_TRADE_HEADERS = (
    "Entered",
    "Exited",
    "Entry price",
    "Exit price",
    "Profit %",
    "Exit reason",
)
BACKTEST_ACTIVITY_TITLE = "Activity"
BACKTEST_PAIR_REQUIRED = "Pair: use BASE/QUOTE, for example BTC/USD."
BACKTEST_RESULT_HEADERS = (
    "Indicator",
    "Timeframe",
    "Params",
    "Net %",
    "Fees $",
    "Open",
    "Wins",
    "Losses",
    "Win %",
    "TSL",
    "TSL Hits",
    "TSL Hit %",
    "Strength",
    "Show Chart",
    "Create Bot",
)
BACKTEST_SHOW_CHART = "Show Chart"
BACKTEST_SHARE = "Share"
BACKTEST_SHARE_TIP = "Export the filtered results table as a PNG image."
BACKTEST_SHARE_DIALOG = "Export backtest results"
BACKTEST_SHARE_FILTER = "PNG image (*.png)"
BACKTEST_SHARE_DONE = "Saved {name} under {path}."
BACKTEST_SHARE_NEED_ROWS = "Run a scan and keep at least one row visible before sharing."
BACKTEST_STRENGTH_HELP = (
    "Indicator Strength 0–100: Wilson lower bound of win rate "
    "(rewards more trades) × (1 − TSL-hit share)^1.5 "
    "(penalizes exits that only happen via trailing stop)."
)
BACKTEST_BH_LABEL = "B&H  ← buy & hold"
FLEET_EXCHANGE = "Exchange"
FLEET_STAKE = "Stake (USD)"
FLEET_STAKE_HELP = "Starting equity for each strategy trial (same as the API fleet default)."
FLEET_BACKTEST_RUN = "Run fleet sweep"
FLEET_BACKTEST_RUNNING = "Fleet sweep running…"
FLEET_BACKTEST_DONE = "Fleet sweep finished."
FLEET_BACKTEST_FAILED = "The fleet sweep did not finish. Check inputs and network, then try again."
FLEET_BACKTEST_NOTE = (
    "Fleet pass 1 tries every strategy on every timeframe (30-day window). "
    "Param optimize and trailing-stop sweep run on the host API, not in this slice."
)
FLEET_BACKTEST_EMPTY_TITLE = "No fleet results yet"
FLEET_BACKTEST_EMPTY_BODY = "Choose a pair and stake, then press Run fleet sweep."
FLEET_BACKTEST_TOP_TITLE = "Top 10 vs buy & hold"
FLEET_BACKTEST_TOP_HEADERS = (
    "Rank",
    "Strategy",
    "Timeframe",
    "Net profit",
    "Trades",
    "vs B&H ($)",
)
FLEET_BUY_HOLD = "Buy & hold baseline: {net}"
FLEET_CREATE_BOT = "Create bot from row"
FLEET_CREATE_BOT_SENT = "Plan builder opened with this row. Review fields, then Add bot."
FLEET_CREATE_BOT_BLOCKED = (
    "This row cannot map to the plan form yet. Adjust fields manually on Plan."
)

PLAN_TITLE = "Plan builder"
PLAN_SUBTITLE = "Build the bots the host should run. Each save makes a new plan version on this PC."
PLAN_NAME = "Bot name"
PLAN_NAME_HELP = "1 to 40 characters. Each bot needs its own name."
PLAN_TIMEFRAME = "Timeframe"
PLAN_INDICATOR = "Indicator"
PLAN_STAKE = "Stake (USD)"
PLAN_STAKE_HELP = "More than 0, up to 100,000."
PLAN_STOP = "Trailing stop (%)"
PLAN_STOP_HELP = "0 turns it off. Otherwise 1 to 20."
PLAN_ADD = "Add bot"
PLAN_APPLY = "Apply edits"
PLAN_REMOVE = "Remove selected bot"
PLAN_SAVE = "Save locally"
PLAN_SEND = "Send to host"
PLAN_STAKE_MODE = "Stake type"
PLAN_STAKE_MODE_HELP = "Fixed USD per entry, or a percent of equity on the host."
PLAN_STAKE_FIXED = "Fixed USD"
PLAN_STAKE_PERCENT = "Percent of equity"
PLAN_STAKE_PCT_HELP = "More than 0, up to 100."
PLAN_BOT_UPDATED = "Updated {name}. Save the plan to keep this change."
PLAN_EMPTY_TITLE = "No bots in this plan yet"
PLAN_EMPTY_BODY = "Fill in the bot form, then press Add bot. Save the plan when every bot is in it."
PLAN_HEADERS = (
    "Name",
    "Pair",
    "Timeframe",
    "Indicator",
    "Stake",
    "Trailing stop (%)",
)
PLAN_BOT_ADDED = "Added {name}. Add another bot or save the plan."
PLAN_BOT_REMOVED = "Removed {name}. Save the plan to keep this change."
PLAN_SAVED = "Saved plan version {version} with {count} bot(s). Reference {digest}."
PLAN_NEEDS_OWNER = "Set your owner ID in Settings before you save a plan."
PLAN_NOT_SENT = "Saved on this PC only."
PLAN_SEND_NO_HOST = "Set a host address in Settings and finish pairing before sending."
PLAN_SEND_UNREACHABLE = "The host did not answer. Check the address and try again."
PLAN_SEND_REFUSED = "The host refused this plan. Check the owner ID and secret."
PLAN_SEND_STALE = "The host already has a newer plan version. Save again, then send."
PLAN_SENT = "Sent plan version {version} to the host. Reference {digest}."
PLAN_LOAD_BLOCKED = "Saving is off until the plan file is fixed. Move plan.json aside, then reopen."

STATUS_TITLE = "Bots"
STATUS_SUBTITLE = (
    "Create bots from Scanner or Backtest, or add one manually. "
    "When a host is linked, status and controls sync from it."
)
STATUS_BOTS = "Live bots"
STATUS_JOURNAL = "Journal"
STATUS_BOT_HEADERS = ("Name", "Pair", "State", "Equity")
STATUS_JOURNAL_HEADERS = ("Time", "Pair", "Side", "Profit", "Source")
STATUS_BOTS_EMPTY_TITLE = "No bots stored on this PC"
STATUS_BOTS_EMPTY_BODY = "Create a bot from a Scanner or Backtest row, or tap Add bot below."
STATUS_GO_PLAN = "Add bot"
BOTS_BUILDER_TITLE = "Bot builder"
BOTS_FAB_ADD = "Add bot"
BOTS_PERF_TITLE = "Performance"
BOTS_PERF_HEADERS = ("Bot", "Pair", "Strategy", "Trades", "Win %", "Realized")
BOTS_PERF_EMPTY_TITLE = "No trade credit yet"
BOTS_PERF_EMPTY_BODY = "Closed trades keep counting toward a bot even after you remove it."
STATUS_JOURNAL_EMPTY_TITLE = "No trades yet"
STATUS_JOURNAL_EMPTY_BODY = "Trades appear here after a bot places one."
STATUS_BOT_CARD = "State: {state}. Equity: {equity}."
STATUS_BOT_CARD_DENSE = (
    "State: {state}. Strategy: {strategy}. Equity: {equity}. "
    "Realized: {realized}. Unrealized: {unrealized}."
)
STATUS_ACTION_PLAY = "Play"
STATUS_ACTION_PAUSE = "Pause"
STATUS_ACTION_DELETE = "Delete"
STATUS_ACTION_HOST_TIP = "Needs a linked host. Not available on this PC alone."
STATUS_ACTION_HOST_BUSY = "Sending command…"
STATUS_ACTION_FAILED = "The host did not accept that command."
STATUS_HOST_CONTROLS = "When a host is linked, Play and Pause call the host. This page still shows bots stored on this PC."
STATUS_HOST_POLL = "Host plan v{version} · {events} pending event(s)."
STATUS_HOST_OFFLINE = "Host configured but not reachable right now."
SETTINGS_CERT_PIN = "Host certificate pin (SHA-256)"
SETTINGS_CERT_PIN_HELP = (
    "Required for https:// hosts. Paste the fingerprint from the host setup guide."
)

SETTINGS_TITLE = "Settings"
SETTINGS_SUBTITLE = "Owner, host, appearance, exchange keys, and privacy for this PC."
SETTINGS_OWNER = "Owner ID"
SETTINGS_OWNER_HELP = "Letters, numbers, dashes, or underscores. 1 to 64 characters."
SETTINGS_HOST = "Host address (optional)"
SETTINGS_HOST_HELP = "An https:// address. Leave it empty until the host is set up."
SETTINGS_SAVE = "Save settings"
SETTINGS_FIRST_RUN = "Set your owner ID to start. Plans are tied to it."
SETTINGS_SAVED = "Settings saved."
SETTINGS_NO_SECRET = (
    "The setup wizard saves the owner secret in Windows Credential Manager, never in a file."
)
SETTINGS_WIZARD = "Open setup wizard"
SETTINGS_WIZARD_HELP = (
    "Guided first-time setup. Each finished step is saved, so you can stop and resume."
)
SETTINGS_THEME = "Theme"
SETTINGS_THEME_HELP = "Follow Windows, or choose light or dark for this app."
THEME_SYSTEM = "Follow Windows"
THEME_LIGHT = "Light"
THEME_DARK = "Dark"
SETTINGS_ACCENT = "Accent color"
SETTINGS_ACCENT_HELP = "Colors the focus ring and the edge of the open section."
SETTINGS_CONNECTION = "Connection"
SETTINGS_APPEARANCE = "Appearance"
SETTINGS_USE_UTC = "Show times in UTC"
SETTINGS_USE_UTC_HELP = (
    "When off (default), timestamps use this PC’s local time zone. When on, show UTC instead."
)
SETTINGS_DASHBOARD_MODULES = "Dashboard modules"
SETTINGS_DASHBOARD_MODULES_HELP = (
    "Minimum size for each Dashboard module in square grid cubes (width × height). "
    "Overrides apply on resize and when loading a layout."
)
SETTINGS_DASHBOARD_RESET_MINS = "Reset module mins to defaults"
SETTINGS_DASHBOARD_SAVE_MINS = "Save module mins"
SETTINGS_DASHBOARD_MINS_SAVED = "Module minimum sizes saved."
SETTINGS_DATA = "Data"
SETTINGS_CUSTOMIZE_HINT = (
    "Checked modules are placed on any Dashboard page. "
    "Categories hint which page type each module fits. "
    "Uncheck to remove; add missing modules to this page."
)
ACCENT_DEFAULT = "TrendAlgo (default)"
ACCENT_NAMES: tuple[str, ...] = ("Blue", "Green", "Amber", "Red", "Violet")
ABOUT_TITLE = "About"
ABOUT_VERSION = "Version {version}"
ABOUT_BODY = (
    "TrendAlgo Bot is free and open source (MIT). Scans and backtests run on this PC. "
    "A headless host you control can run an approved plan. This app never stores exchange keys."
)
ABOUT_DONATE = (
    "Optional donations support the project. Venmo is welcome when you choose to give — "
    "never required."
)
ABOUT_VENMO = "Donate with Venmo"
ABOUT_CHECK_UPDATES = "Check for updates"
ABOUT_CHANGELOG = "Changelog"
ABOUT_UPDATE_CHECKING = "Checking for updates…"
ABOUT_UPDATE_CURRENT = "You’re on the latest version."
ABOUT_UPDATE_ERROR = "Could not check for updates. Try again later."
ABOUT_UPDATE_AVAILABLE = "Update {version} is available."
ABOUT_UPDATE_TITLE = "TrendAlgo"
ABOUT_UPDATE_BODY = "A newer installer ({version}) is available."
ABOUT_UPDATE_DOWNLOAD = "Download and install"
ABOUT_UPDATE_LATER = "Later"
ABOUT_DONATE_PROMPT = (
    "If TrendAlgo helps you, you can support the project. Optional — never required."
)
ABOUT_DONATE_ACCEPT = "Donate"
ABOUT_DONATE_LATER = "Not now"
SETTINGS_PRIVACY = "Privacy"
TRAY_SHOW = "Show TrendAlgo"
TRAY_SCANNER = "Open scanner"
TRAY_QUIT = "Quit"
TRAY_QUIT_TITLE = "Quit TrendAlgo?"
TRAY_QUIT_BODY = (
    "Quitting stops auto-scan and closes the tray icon. Confirmed exit also stops any scan "
    "that is still running. Close the window instead to keep scanning in the tray."
)
TRAY_HIDDEN = "TrendAlgo is still running in the system tray."
AUTOSCAN_NEXT = "Next auto-scan in {minutes} min."
AUTOSCAN_PAUSED = "Auto-scan paused (scan running)."
AUTOSCAN_OFF = "Auto-scan waits until a scan finishes."
NOTIFY_SECTION = "Alerts and notifications"
NOTIFY_SECTION_HELP = (
    "Per event kind: enable Windows toast and/or Telegram. Logs default off to avoid spam. "
    "Alerts history still records events on the Alerts tabs."
)
NOTIFY_COL_WINDOWS = "Windows"
NOTIFY_COL_TELEGRAM = "Telegram"
NOTIFY_KIND_LOGS = "Scan / backtest logs"
NOTIFY_KIND_ENTERED = "New qualified entries"
NOTIFY_KIND_LEFT = "Left qualified (watchlist)"
NOTIFY_KIND_TRADES = "Trade alerts"
NOTIFY_WATCHLIST = "Watchlist leave alerts"
NOTIFY_QUALIFIED = "Qualified enter alerts"
NOTIFY_TRADES = "Trade fill alerts"
NOTIFY_TELEGRAM = "Enable Telegram for checked kinds"
NOTIFY_TG_WATCHLIST = "Telegram: watchlist"
NOTIFY_TG_QUALIFIED = "Telegram: qualified"
NOTIFY_TG_TRADES = "Telegram: trades"
NOTIFY_START_WINDOWS = "Start with Windows"
NOTIFY_START_WINDOWS_HELP = (
    "Open TrendAlgo at login so tray auto-scan can resume. Default is on for this PC."
)
NOTIFY_TELEGRAM_WIZARD = "Set up Telegram…"
NOTIFY_SAVED = "Notification settings saved."
TG_WIZARD_TITLE = "Telegram alerts"
TG_WIZARD_INTRO = (
    "Copy each box into Telegram, then paste the token and chat id below. "
    "Secrets stay in Windows Credential Manager — never in a profile file."
)
TG_WIZARD_STEP1 = "1. Create bot & token"
TG_WIZARD_STEP1_HELP = (
    "Open BotFather, paste the commands in order. BotFather replies with a token "
    "(looks like 123456:ABC…). Paste that token below. If the username is taken, "
    "change the middle letters but keep the ending bot."
)
TG_WIZARD_STEP2 = "2. Chat id"
TG_WIZARD_STEP2_HELP = (
    "BotFather does not give a chat id. Paste /start into your new bot, then Detect — "
    "TrendAlgo clears any webhook with your token and reads getUpdates. "
    "Optional: copy the deleteWebhook URL and open it in a browser first."
)
TG_WIZARD_STEP3 = "3. Test & save"
TG_WIZARD_COPY = "Copy"
TG_WIZARD_SNIP_NEWBOT = "Paste into BotFather"
TG_WIZARD_SNIP_NAME = "When asked for a name"
TG_WIZARD_SNIP_USER = "When asked for a username"
TG_WIZARD_SNIP_MYBOTS = "If you need the token again"
TG_WIZARD_SNIP_START = "Paste into your new bot chat"
TG_WIZARD_SNIP_DELETE_WH = "Optional: open in browser to clear webhook"
TG_WIZARD_DELETE_WH_PLACEHOLDER = "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
TG_WIZARD_OPEN_DELETE_WH = "Open deleteWebhook URL"
TG_WIZARD_BOTFATHER = "Open BotFather"
TG_WIZARD_TOKEN = "Bot token"
TG_WIZARD_CHAT = "Chat id"
TG_WIZARD_DETECT = "Detect chat id"
TG_WIZARD_TEST = "Send test message"
TG_WIZARD_SAVE = "Save and sync to host"
TG_WIZARD_OK = "Telegram is ready."
TG_WIZARD_FAIL = "Telegram could not send. Check the token and chat id."
TG_WIZARD_DETECT_FAIL = (
    "No chat found. Webhook was cleared if the token is valid. "
    "Open your bot, send /start, then Detect chat id again."
)
TG_WIZARD_NEED_TOKEN = "Paste the bot token first."
TG_WIZARD_SAVED = "Saved to Credential Manager."
TG_WIZARD_SYNC_OK = "Host received Telegram credentials for trade alerts."
TG_WIZARD_SYNC_SKIP = "Host not configured — credentials stay on this PC only."
ALERT_ENTER_TITLE = "Qualified: {symbol}"
ALERT_LEAVE_TITLE = "Left watchlist: {symbol}"
ALERT_TRADE_TITLE = "Trade: {pair}"
SCANNER_ALERTS_HEADERS = ("When", "Kind", "Symbol", "Detail")
SCANNER_ALERTS_EMPTY_TITLE = "No alerts yet"
SCANNER_ALERTS_EMPTY_BODY = (
    "After each scan, newly qualified coins and watchlisted coins that drop out appear here."
)
CAL_WIZARD_TITLE = "Calendar API setup"
CAL_WIZARD_NEXT = "Next"
CAL_WIZARD_BACK = "Back"
CAL_WIZARD_SKIP = "Skip"
CAL_WIZARD_FINISH = "Finish"
CAL_WIZARD_OPEN_DOCS = "Open docs"
CAL_WIZARD_KEY = "API key"
CAL_WIZARD_TOKEN = "Access token"
CAL_WIZARD_TEST = "Test"
CAL_WIZARD_SAVE = "Save"
CAL_WIZARD_TEST_OK = "Connection OK."
CAL_WIZARD_TEST_FAIL = "Test failed: {detail}"
CAL_WIZARD_SAVED = "Saved to Credential Manager."
CAL_WIZARD_NEED_TEST = "Test the key successfully before saving."
CAL_EVENTS_EMPTY = "No upcoming events match your filters."
CAL_EVENTS_NO_KEYS = "Connect CoinMarketCal or Coindar to load crypto event dates."
CAL_EVENTS_REFRESH = "Refresh events"
CAL_FILTER_HOLDINGS = "My holdings"
CAL_FILTER_30D = "30D"
CAL_FILTER_IMPACT = "Medium+"
CAL_SORT_DATE = "Date"
CAL_SORT_IMPACT = "Impact"
CAL_SORT_POP = "Popularity"
