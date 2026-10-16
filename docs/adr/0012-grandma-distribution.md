# ADR-0012 — Grandma-friendly distribution (hosted first)

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Product owner + agent session

## Context

TrendAlgo is a Python API + browser PWA. Expert users can run `dev-local` / `preview-local`. Non-expert (“grandma”) users cannot be expected to install Python, Node, or manage two terminals. Template winget/EXE naming exists, but no installer ships yet.

## Decision

1. **Primary grandma path:** hosted dry-run website (Docker/VPS already in ADR-0002) — open a link, no keys for Scanner.
2. **Secondary path:** one-click local launcher (Windows portable/NSIS + Linux AppImage) that starts the same API and opens the PWA — not a separate Electron/Tauri product rewrite.
3. **Defer:** Winget submission, code signing, and full native shell until launcher assets exist.

## Alternatives considered

| Option | Why not first |
|--------|----------------|
| Electron/Tauri rewrite | High packaging cost; duplicates the PWA |
| Expert-only `uv`+`npm` forever | Blocks non-expert adoption |
| Static GitHub Pages alone | No API → Bot/Scanner cannot load |

### Critique

| Issue | Resolution |
|-------|------------|
| Hosted URL not live yet | Document operator steps in FIRST_RUN_USER + DEPLOYMENT; HUMAN provisions VPS |
| Local launcher scope creep | BUILD_PLAN packaging sprint; wrap existing stack only |
| Proprietary SDKs | FOSS MIT path only; no Crashlytics/Sentry on production |

## Consequences

- End-user docs emphasize “open the link” and “no exchange keys for Scanner”.
- About-panel update checker can later point at `{Prefix}-x64-setup.exe` once CI builds it.
- H-006 / H-023 still block public beta marketing, not dry-run hosted demos.

## Amendment (2026-10-08) — operator testing

For **operator / home-PC testing**, prefer the Windows launcher and same-origin serve (`TRENDALGO_SERVE_WEB`) per [ADR-0014](0014-local-windows-first.md). Hosted grandma URL remains the share-with-others path once HUMAN provisions VPS; it is not required to validate Scanner locally.
