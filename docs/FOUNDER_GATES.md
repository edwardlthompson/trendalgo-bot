# Founder Gates — TrendAlgo Bot

Machine-readable gates for H-001–H-034. **Human actions:** [`docs/HUMAN_BACKLOG.md`](HUMAN_BACKLOG.md) (not listed in BUILD_PLAN sprint lanes).

## Commands

| Command | Purpose |
|---------|---------|
| `bash scripts/founder-gate.sh status` | All H-IDs: pending / preflight_ok / approved / backlog |
| `bash scripts/check-human-backlog.sh [--sprint N]` | AUTO preflight for sprint H-IDs |
| `bash scripts/check-risk-mitigations.sh [--strict]` | Risk catalog verification |
| `bash scripts/founder-gate.sh approve H-007` | One-command approve (after preflight PASS) |
| `python scripts/founder_gate.py approve-all-soft` | Batch approve soft gates (after preflights PASS) |
| `bash scripts/founder-gate.sh approve-bundle pre-sprint-1` | H-001, H-005, H-007 batch |

## Gate types

| Type | H-IDs | Rule |
|------|-------|------|
| **Hard** | H-006, H-023, H-010, H-028, H-008, H-011, H-031, H-032 | Never AUTO-approve |
| **Soft** | H-007–H-025, H-030, H-034 sprint gates | AUTO preflight + `approve` |
| **Non-blocking** | H-002 | Optional |

## Permanent controls (not open risks)

| Control | Script | Cadence |
|---------|--------|---------|
| Legal compliance grep | `check-legal-compliance.sh` | Sprint 0 sign-off, release |
| Go-live | `go-live-gate.sh` | Every live enable |
| Sprint scope | `sprint-preflight.sh` | Start of each sprint |
| Risk strict | `check-risk-mitigations.sh --strict --sprint N` | Sprint sign-off |
| Production cost | `check-production-cost.sh` | Monthly (H-027) |

State file: `.cursor/founder-gates.json` (gitignored).
