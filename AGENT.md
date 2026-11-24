# AGENT.md — original product brief (Sacred)

Copy this file to `AGENT.md` after clone and **before** `init-project`. Paste the
human’s original prompt **verbatim**. Bootstrap stamps `AGENTS.md` only and will
not overwrite this file. Later sessions: read this before any BUILD_PLAN sprint row.

<!-- agent-brief:one-liner -->
Self-hosted crypto trading platform: native CCXT engine, LTS opportunity scanner, Secret Sauce Lab, and desktop shell.
<!-- /agent-brief:one-liner -->

<!-- agent-brief:keywords -->
crypto, trading, scanner, portfolio
<!-- /agent-brief:keywords -->

## Rules

- Dry-run is the default; live orders require `TRENDALGO_MODE=live` and per-exchange `go-live-gate.sh --approve`.
- Secret Sauce must beat fees and Buy & Hold under an honest Oracle ceiling (never force-sorted).
- Dual-runtime desktop architecture (ADR-0021): C# Avalonia shell + permanent Python Research Engine sharing `results.db`.
- Do not overwrite live `branding/assets/*.svg` (Sacred vector SoT).

## First milestone

Kraken public research desk + 9-CEX read-only portfolio + Secret Sauce Lab + Avalonia/PySide6 desktop parity.
