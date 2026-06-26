# ADR-0006: LTS Absorption — Opportunity Scanner

- **Status:** Proposed (H-013 approval Sprint 4.5)
- **Date:** 2026-06-25

## Context

`linear-trend-spotter` repo duplicates scanner logic; merge into TrendAlgo as first-class module.

## Decision

1. Vendor LTS as submodule or pinned dep; map to `src/trendalgo/scanner/`.
2. Preserve `qualified_snapshot.json` contract and import boundaries.
3. Replace standalone `main.py` / Render worker with APScheduler on VPS.
4. Deprecate standalone repo after H-014 parity validation.

## Consequences

Sprint 4.5; `docs/LTS_INTEGRATION.md`, `docs/LTS_ABSORPTION.md`; `lts-parity-check.sh`.
