# ADR-0021 — Avalonia shell + permanent Python Research Engine

- **Status:** Accepted
- **Date:** 2026-11-18
- **Relates to:** ADR-0016 (device/host split; shell chrome path amended), ADR-0015 (retired pywebview), ADR-0018 (ELv2), ADR-0008/0017 (monetization)
- **Inventory:** [`docs/PRODUCT_SURFACE_INVENTORY.md`](../PRODUCT_SURFACE_INVENTORY.md) (v1.19.0 freeze)

## Context

PySide6 `QTableWidget` boards struggle at All-TA / Sauce scale. Operators need Win/Linux/macOS grids with virtualization, while indicator quality and catalog size must not shrink. Rewriting pandas_ta / All-TA in C# was rejected.

## Decision

1. **Dual-runtime forever** (until a future ADR says otherwise): **C# Avalonia** owns desktop chrome; **Python** remains the Research Engine (CCXT, OHLCVT, SIGNAL_REGISTRY / All-TA, Sauce, billing math, go-live/founder gates).
2. **Shared truth:** profile `results.db` + versioned IPC handshake. UI never owns strategy math; engine never owns chrome.
3. **License:** ELv2 (ADR-0018). Monetize official builds + Alpha Share; community PRs on `engine` / `shell` lanes.
4. **P0–P2** in the Avalonia plan are **accepted product requirements**. **P3+** is architecture backlog (run IDs, plugin UI slots, query layer, export pipeline hooks required in schema/IPC).
5. **Parity gate:** Avalonia must cover every **Real** surface in the inventory (§12) before PySide6 chrome retires. Orphans stay out of P0. CredMan targets and lane DBs keep their contracts; migrate only with adapters.
6. **Amend ADR-0016:** local control surface becomes Avalonia + bundled engine; Study/Sauce remain first-class desktop surfaces. Headless `botd` host unchanged.

### Non-goals

- No pandas_ta reimplementation in C#.
- No Chromium primary shell.
- No untrusted strategy marketplace.
- No auto fee collection or withdrawal-key custody.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Stay PySide6 + virtualized Qt models only | Cross-platform installer + Excel-class grids remain weak |
| Full C# rewrite of indicators | Quality/catalog risk; forever dual-runtime avoids it |
| Electron / Tauri | Heavier; Chromium primary rejected |
| Cull All-TA catalog for speed | Forbidden; use `results.db` streaming instead |

## Consequences

- New tree: `shell/` (Avalonia) + `src/trendalgo/results_store/` (schema/IPC).
- Official builds pin shell semver ↔ engine version handshake.
- PySide6 stays shippable until inventory P0 checklist is ✅.
- BUILD_PLAN Sequential: ADR → contract → P0 grids → parity port → packaging.

### Critique

| Issue | Resolution |
|-------|------------|
| Losing TradFi/FX/AlgoSpecial | Inventory §12 desks required in P0 |
| Python sidelined later | Catalog cuts forbidden; engine is a release artifact |
| CredMan / prefs break | Inventory §10 frozen; adapters only |
| P3+ vapor | Hooks in schema/IPC now; implement after P2 |
| Empty/error/loading | Job status + empty grids from IPC/DB |
