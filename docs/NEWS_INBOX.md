# News Inbox

Auto-collected inbox of news, upstream updates, security fixes, and ideas relevant to this repo, appended daily by News Bot.
A Cursor planning agent should review these items and fold the useful ones into BUILD_PLAN; entries are append-only, newest at the bottom.


## 2026-11-13

**News and updates**

- Coinigy breach: users told to revoke every exchange API key ever connected, including read-only keys. [source](https://insights.coinigy.com/urgent-revoke-your-exchange-api-keys-connected-to-coinigy/)

**Tasks for the planning agent**

- [ ] Add API-key hygiene guidance to security docs — Third-party key leaks show why bot keys need no-withdraw, IP allowlists, and no reuse. Label: `[AGENT]` · Priority: P2 · https://insights.coinigy.com/urgent-revoke-your-exchange-api-keys-connected-to-coinigy/

## 2026-11-14

**News and updates**

- FastAPI 0.162.6 drops Python 3.10; 0.162.7 fixes async yield-dependency cleanup on request cancellation. [source](https://github.com/fastapi/fastapi/releases/tag/0.162.7)
- Kraken deprecates the Derivatives WebSocket v1 (removal 2027-03-01) in favour of the Unified WebSocket. [source](https://docs.kraken.com/exchange/changelog)

**Tasks for the planning agent**

- [ ] Bump FastAPI to 0.162.7 — Fixes async yield-dependency cleanup on cancellation; safe on Python 3.12. Label: `[AGENT]` · Priority: P3 · https://github.com/fastapi/fastapi/releases/tag/0.162.7
- [ ] Plan the move off Kraken Derivatives WebSocket v1 — v1 is removed on 2027-03-01; any futures streaming must switch to the Unified WebSocket. Label: `[AGENT]` · Priority: P3 · https://docs.kraken.com/exchange/changelog
