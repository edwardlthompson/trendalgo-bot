# BUILD_PLAN cleanup

After a sprint's AGENT rows are all ✅ and gates pass, move detail out of the active board.

## When to run

- End of `/build` (step 5) when every task in the current sprint is ✅
- `/audit` step 4 and `/push` step 5 cleanup
- Any time the active board still lists checked-off sprint task lists

## Steps

1. Confirm the sprint has **no** 🔲 or ❌ numbered tasks remaining.
2. Run:

```bash
python scripts/archive-build-plan-sprint.py --dry-run
python scripts/archive-build-plan-sprint.py
```

Optional: `--sprint S19` to archive one sprint only.

3. Verify:
   - Active `BUILD_PLAN.md` section contains **only open sprints** (task lists for done sprints removed)
   - `COMPLETED_TASKS.md` has a new `## Sprint …` section at the top
   - **Completed —** summary table and **Archived sprints** row updated
   - **Current sprint** header points at the next open sprint

## Manual fallback

If the script cannot parse a sprint block, archive by hand per @docs/FOR_AGENTS.md: copy ✅ rows to @COMPLETED_TASKS.md, delete the ### Sprint block from active, update Archived Sprints.

Begin now.
