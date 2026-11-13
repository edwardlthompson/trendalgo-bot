# Spec: Secret Sauce helpers → Final Boss

> Status: Final Boss roadmap in progress (S1–S6). Phase 0–2 Lab foundations remain shipped.
> Feature notebook: [`docs/features/secret-sauce.md`](../features/secret-sauce.md)
> Board: `BUILD_PLAN.md` → **SS-Final-Boss**

## Locked decisions

- Helpers + **Secret Sauce Final** (fee re-sim combiner) — not a Net % average of helpers.
- Do **not** clone Oracle entry/exit indexes; no HL / fee-free fills for Sauce.
- Never force-sort Sauce/Final to #2; spectrum note only.
- Exact catalog clone still forbidden (`is_exact_peer_clone`).
- **No Sauce `time_budget_s` hard caps** — helpers and Final run to completion (finite seed lists bound work).
- **Out of scope forever:** **M** BTC/corr veto · **R** cross-coin transfer warm-start.

## Helper rows (fee-valid → Results + Study)

| Row | Skill |
|-----|--------|
| Secret Sauce TA | Oracle×catalog coincidence (existing) |
| Secret Sauce Lab | Core mine / refine |
| Secret Sauce Peer | **A** — mutated top peer entry; search exits + TSL |
| Secret Sauce Armed | **B** — higher-TF / regime arming ∧ entry |
| Secret Sauce Exit | **C** — seed from Sauce TA / Peer; heavy adaptive exit + trail |
| Secret Sauce Final | **E/O** — vote (≥2 agree ±1) or best-holdout; dedicated exit+TSL; fee re-sim |
Create-bot prefers **Final** when present (`create_bot_sauce_preference`).

## Sprint map

| ID | Sprint | What |
|----|--------|------|
| A, C | S2 | Peer-entry + Exit handoff |
| B, L, K | S3 | Armed; TSL 0–20%; holdout-first pick / Oracle-TF 5% bias |
| E/O | S4 | Final Boss + Study voters + chart radios |
| G, I, J, N, H | S5 | Dual-horizon; regime peers; CCI/WILLR/MFI; session mask; scale-out proxy |
| P, Q, S, T, U, V | S6 | Teacher; genetic; MFE exit; vol targeting; veto; meta-TSL |
## Honesty locks (unchanged)

- Residual-driven selective features only; no bulk catalog bank in Lab search.
- Closing the gap to Oracle **HL** Net % is not the honesty goal.
- Under top peer → still publish with `spectrum_note`.
- Empty helpers: Final degrades to Core; omit missing votes; never leave pending after join.

## Validation

```bash
uv run pytest tests/test_backtest/test_secret_sauce_helpers_final.py \
  tests/test_backtest/test_secret_sauce_lab.py \
  tests/test_device/test_sauce_names.py \
  tests/test_device/test_secret_sauce_smoke.py -q
python scripts/agent-run.py watch-agent-gates --once --autofix --scope auto

```
