# News Inbox

Auto-collected inbox of news, upstream updates, security fixes, and ideas relevant to this repo, appended daily by News Bot.
A Cursor planning agent should review these items and fold the useful ones into BUILD_PLAN; entries are append-only, newest at the bottom.


## 2026-11-13

**News and updates**

- Coinigy breach: users told to revoke every exchange API key ever connected, including read-only keys. [source](https://insights.coinigy.com/urgent-revoke-your-exchange-api-keys-connected-to-coinigy/)

**Tasks for the planning agent**

- [x] Add API-key hygiene guidance to security docs — Third-party key leaks show why bot keys need no-withdraw, IP allowlists, and no reuse. Label: `[AGENT]` · Priority: P2 · https://insights.coinigy.com/urgent-revoke-your-exchange-api-keys-connected-to-coinigy/ (synced to BUILD_PLAN)

## 2026-11-14

**News and updates**

- FastAPI 0.162.6 drops Python 3.10; 0.162.7 fixes async yield-dependency cleanup on request cancellation. [source](https://github.com/fastapi/fastapi/releases/tag/0.162.7)
- Kraken deprecates the Derivatives WebSocket v1 (removal 2027-03-01) in favour of the Unified WebSocket. [source](https://docs.kraken.com/exchange/changelog)

**Tasks for the planning agent**

- [ ] Bump FastAPI to 0.162.7 — Fixes async yield-dependency cleanup on cancellation; safe on Python 3.12. Label: `[AGENT]` · Priority: P3 · https://github.com/fastapi/fastapi/releases/tag/0.162.7
- [ ] Plan the move off Kraken Derivatives WebSocket v1 — v1 is removed on 2027-03-01; any futures streaming must switch to the Unified WebSocket. Label: `[AGENT]` · Priority: P3 · https://docs.kraken.com/exchange/changelog

## 2026-11-15

**News and updates**

- FastAPI 0.163.0 adds per-dependency concurrency limits (`Depends(max_concurrency=...)`); 0.163.1 fixes OpenAPI for nested computed fields. [source](https://github.com/fastapi/fastapi/releases/tag/0.163.0)
- Gate.io SDK typosquats on PyPI (gateio-sdk, gateio-v4, gateio-client, gateio-ws, gatepay-sdk-python at "99.99.x") steal host info and env variables at install time. [source](https://github.com/advisories/GHSA-xjgf-m5q9-6gpf) · [more](https://github.com/advisories/GHSA-8chm-xj53-hg7h)

**Tasks for the planning agent**

- [ ] Bump fastapi to 0.163.1 and throttle exchange-hitting endpoints with Depends(max_concurrency=...) — Replaces ad-hoc locks around portfolio sync and backtest triggers with a built-in limit. Label: `[AGENT]` · Priority: P3 · https://github.com/fastapi/fastapi/releases/tag/0.163.0
- [ ] Confirm Gate.io access goes only through ccxt and keep installs locked — No gate SDK should appear in uv.lock, and `uv sync --locked` (no ad-hoc pip installs of exchange SDKs on the VPS) blocks these typosquats. Label: `[AGENT]` · Priority: P3 · https://github.com/advisories/GHSA-xjgf-m5q9-6gpf

## 2026-11-16

**News and updates**

- Proxima post-mortem: a debug log line wrote wallet private keys, production logging went to DEBUG, and an exposed SigNoz instance leaked them (5,324 SOL from 870 wallets, Nov 14). [source](https://cryptowatchdesk.com/news/security-alert-proxima-post-mortem-debug-logs-held-private-keys-5324-sol-181-users-firewall-rule-removed)
- Kraken Futures removes POST /withdrawal and GET /transfers on Nov 30 (use POST /transfer and GET /transfer/assets); Maker Protection rejections now return `makerProtectionOrderLimitExceeded` instead of `tooManyOrders`. [source](https://docs.kraken.com/exchange/changelog)

**Tasks for the planning agent**

- [x] Extend SecretRedactor to wallet private keys, seed phrases and vaulted keys at every log level — SecretRedactor masks only watched env values today, so add pattern-based masking plus a test that DEBUG output of wallet/DEX and exchange-key paths holds no secrets, and keep any log UI on the VPS bound to localhost. Label: `[AGENT]` · Priority: P2 · https://cryptowatchdesk.com/news/security-alert-proxima-post-mortem-debug-logs-held-private-keys-5324-sol-181-users-firewall-rule-removed (synced to BUILD_PLAN)
- [ ] Confirm nothing calls Kraken Futures /withdrawal or /transfers and map makerProtectionOrderLimitExceeded to a backoff — Avoids a silent break on Nov 30 and stops the new error being read as an open-order-limit failure. Label: `[AGENT]` · Priority: P3 · https://docs.kraken.com/exchange/changelog
