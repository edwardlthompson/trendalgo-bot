# P2 backend integrations

## Endpoints

- `POST /api/v1/webhooks/telegram` accepts Telegram update JSON, validates the
  message chat against `TELEGRAM_CHAT_ID`, rate-limits by chat, and calls the
  existing status/pause/resume command handler. Configure Telegram's
  `X-Telegram-Bot-Api-Secret-Token` header when `TELEGRAM_WEBHOOK_SECRET` is set.
- `POST /api/v1/hyperopt` returns a queued job containing `job_id`, `status`,
  `error`, and `result`. `GET /api/v1/hyperopt/{job_id}` reports
  `queued|running|failed|done`; failed jobs include an error string.
- `POST /api/v1/webhooks/tradingview` remains log-only unless
  `TV_EXECUTION_ACK=1`. Its response now includes `execution`; acknowledged,
  audited buy/sell signals are sent through the unified paper/live order path.
  Existing live-trading approval and exchange controls still apply.
- `GET /api/v1/portfolio/arbitrage` and
  `GET /api/v1/trading/arbitrage/signals` fetch concurrent public CCXT tickers
  outside dry-run mode. Responses include `pricing_source`,
  `timed_out_venues`, and `failed_venues`. If every live venue fails, the
  response uses the dry-run matrix with `pricing_source=dry_run_fallback`.

## Environment

- `TELEGRAM_CHAT_ID`: allowed chat ID (comma-separated IDs are accepted).
- `TELEGRAM_WEBHOOK_SECRET`: optional Telegram webhook secret-token check.
- `TELEGRAM_RATE_LIMIT_PER_MINUTE`: per-chat limit; default `10`.
- `TV_EXECUTION_ACK`: execution gate; default off and enabled only by `1`.
- `TV_EXECUTION_EXCHANGE`: target exchange; default `kraken`.
- `TV_EXECUTION_AMOUNT_USD`: default signal stake; default `25`.
- `ARBITRAGE_TIMEOUT_SECONDS`: overall live pricing budget; default `8`.
- `TRADINGVIEW_WEBHOOK_SECRET`: required HMAC secret for TradingView ingress.
