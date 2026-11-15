# Grok Bot webhook

Optional, off-by-default notification channel. **Telegram is primary**: it always sends first and independently. A slow or failing Grok Bot POST never delays scanning, trading, or Telegram.

## Env (never commit real values)

| Variable | Default | Purpose |
|----------|---------|---------|
| `GROKBOT_WEBHOOK_URL` | unset (off) | HTTPS URL from the Grok Bot routine panel |
| `GROKBOT_WEBHOOK_KEY` | unset | Sender key; sent as a request header |
| `GROKBOT_WEBHOOK_HEADER` | `Authorization` | Header name |
| `GROKBOT_WEBHOOK_SCHEME` | `Bearer` when header is Authorization; empty otherwise | Prefix before the key |
| `GROKBOT_WEBHOOK_EVENTS` | `all` | Quota filter: `all`, `trades`, `scanner-a`, or a comma list (`trade_entry,trade_exit`) |
| `GROKBOT_WEBHOOK_COOLDOWN_SEC` | `900` | After any non-2xx (including 402/429), timeout, or network error, skip POSTs for this many seconds |

HTTP URLs are refused. POSTs do not follow redirects, so the sender key never hops to a `Location` URL (including plaintext HTTP). The channel is send-only: no exchange keys, no extra balances.

## Grok unavailable

Any non-2xx, timeout, or network error is **Grok unavailable**: one attempt, then cooldown (no retry spam). Failures go to the debug log. If Grok is already on cooldown when Telegram fires, the Telegram body gets a short `AI brief unavailable` note. Owner test (`send_test`) clears cooldown so you can verify after topping up quota.

## Test event

```bash
uv run python -m trendalgo.notifications.grokbot_cli
# or owner-auth POST /api/v1/notifications/grokbot/test
# Device: Settings → Alerts, or Alerts ribbon → Test Grok Bot
```

## Payload (schema_version 1)

```json
{
  "schema_version": "1",
  "event_type": "trade_exit",
  "timestamp_utc": "2026-11-15T00:00:00Z",
  "bot_mode": "dry-run",
  "pair": "BTC/USD",
  "exchange": "kraken",
  "tier": null,
  "uniformity": null,
  "gain": null,
  "gains": null,
  "volume": null,
  "sparkline": null,
  "reason": "MACD cross down",
  "rationale": "MACD cross down",
  "strategy_id": "macd-kraken-1h",
  "entry_price": null,
  "exit_price": 64210.5,
  "stake": 25.0,
  "pnl": 1.15,
  "exit_rule": "MACD cross down",
  "side": "sell"
}
```

`event_type`: `scanner_alert`, `qualified_enter`, `qualified_leave`, `trade_entry`, `trade_exit`, `test`, `refit`, `daily_summary`, `explain_request`, `weekly_digest`, `sweep_complete`, `golive_readiness`, `portfolio_snapshot`.

## Why? button (`explain_request`)

Scanner and trade Telegram alerts include a **Why?** inline button. Telegram still sends first with no wait on Grok. Tapping Why POSTs `explain_request` (same fields as the original event). That POST is **not** filtered by `GROKBOT_WEBHOOK_EVENTS` — use it to spend quota only on alerts you care about.

```json
{
  "schema_version": "1",
  "event_type": "explain_request",
  "timestamp_utc": "2026-11-15T00:00:00Z",
  "bot_mode": "dry-run",
  "pair": "BTC/USD",
  "strategy_id": "macd-kraken-1h",
  "exit_rule": "MACD cross down",
  "reason": "explain trade_exit: MACD cross down",
  "side": "sell"
}
```

Native CCXT engine exits record the rule that fired (`MACD cross down`, `RSI threshold`, …) in the journal `rationale` and in `exit_rule`. That does not change whether an exit happens. Trailing stop / stoploss / scale-out labels appear only if those mixins actually close the trade; the scheduled runner today exits via `strategy.exit()` only.

## Weekly digest (`weekly_digest`)

Off by default. Set `WEEKLY_DIGEST_ENABLED=1` (optional `WEEKLY_DIGEST_DOW=sun`, `WEEKLY_DIGEST_HOUR=0` UTC). Telegram gets a compact weekly note first; Grok gets the same summary in `reason` plus structured counts in `gains`. Filter with `GROKBOT_WEBHOOK_EVENTS=weekly` or `all`.

```json
{
  "schema_version": "1",
  "event_type": "weekly_digest",
  "reason": "TrendAlgo weekly\nEntered: BTC/USD\nLeft: —\nTiers A:3\nTrades: 4  PnL: $+2.10\nTop strategy: macd-kraken-1h $+2.10\nRecurring: BTC/USD",
  "gains": {
    "trade_count": 4,
    "pnl_usd": 2.1,
    "tier_counts": {"A": 3},
    "entered": ["BTC/USD"],
    "left": [],
    "recurring_pairs": ["BTC/USD"]
  }
}
```

## Sweep complete (`sweep_complete`)

Emitted only after an LTS backtest sweep actually returns a summary (not when backtests are skipped, disabled, or raise). Advisory only — ranking and order logic are unchanged. `gains.oos_split` is `null` (no walk-forward split in the LTS sweep). Filter: `GROKBOT_WEBHOOK_EVENTS=sweep`.

```json
{
  "schema_version": "1",
  "event_type": "sweep_complete",
  "reason": "LTS sweep complete: 12 coins, 10 ranked, 2 overfitting flags",
  "gains": {
    "top": [{"symbol": "BTC", "strategy": "MACD", "trades": 14, "win_pct": 57.0, "net_pct": 4.2}],
    "overfitting": [{"symbol": "DOGE", "flags": ["thin_sample", "high_win_thin_sample"], "trades": 3, "win_pct": 100}],
    "oos_split": null,
    "coin_count": 12
  }
}
```

## Go-live readiness (`golive_readiness`)

Owner-auth GET/POST `/api/v1/notifications/golive-readiness`, or `uv run python -m trendalgo.notifications.golive_cli` (`--emit` POSTs). **Advisory only** — it never writes approvals, never calls `scripts/go-live-gate.sh`, and `gains.bypasses_go_live_gate` is always `false`. Filter: `GROKBOT_WEBHOOK_EVENTS=golive`.

```json
{
  "schema_version": "1",
  "event_type": "golive_readiness",
  "reason": "TrendAlgo go-live readiness (advisory; does not approve live) trades=24 hints=...",
  "gains": {
    "advisory": true,
    "bypasses_go_live_gate": false,
    "trade_count": 24,
    "max_drawdown_pct": 0.04,
    "max_losing_streak": 2,
    "fee_assumptions": {"backtest_fee_bps_round_trip": 52, "dry_run_slippage_bps": 0},
    "hints": ["dry-run sample looks populated; run go-live-gate.sh --check-only"]
  }
}
```

## Portfolio snapshot (`portfolio_snapshot`)

Off by default. Set `PORTFOLIO_SNAPSHOT_WEBHOOK=1` to POST after the daily portfolio job. Payload has allocations, concentration, idle stable/fiat share, and non-cash holdings whose asset is not on the current Qualified list (USD/USDT/EUR cash is not listed as off-qualified). No API keys and no account identifiers. Filter: `GROKBOT_WEBHOOK_EVENTS=portfolio`.

```json
{
  "schema_version": "1",
  "event_type": "portfolio_snapshot",
  "reason": "Portfolio snapshot holdings=4 idle_stable=12% top=BTC",
  "gains": {
    "allocations": [{"asset": "BTC", "pct": 0.55}, {"asset": "USD", "pct": 0.12}],
    "concentration": {"top_asset": "BTC", "top_pct": 0.55, "hhi": 0.35},
    "left_qualified": ["DOGE"],
    "idle_stable_share": 0.12,
    "holding_count": 4
  }
}
```

## Filter examples

```bash
GROKBOT_WEBHOOK_EVENTS=trades          # trade_entry + trade_exit (+ test, explain_request)
GROKBOT_WEBHOOK_EVENTS=scanner-a       # LTS Tier A scanner alerts only
GROKBOT_WEBHOOK_EVENTS=all             # default
```
