"""Fail when AVALONIA_PARITY_GAPS AV-G-* IDs drift from BUILD_PLAN rows."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

GAPS_REL = Path("docs/AVALONIA_PARITY_GAPS.md")
PLAN_REL = Path("BUILD_PLAN.md")

GAP_LINE = re.compile(
    r"^-\s+\[(?P<mark>[ xX])\]\s+\*\*(?P<id>AV-G-[A-Z0-9]+)\*\*",
)
OPEN_PLAN = re.compile(
    r"^(?:(?:\d+[a-z]?)\.|-)\s+(?P<status>🔲|❌)\s+"
    r"\[AGENT\](?:\[(?:LOCAL|CLOUD)\])?\s+(?P<id>AV-G-[A-Z0-9]+)\b",
)
DONE_PLAN = re.compile(
    r"^(?:(?:\d+[a-z]?)\.|-)\s+✅\s+"
    r"\[AGENT\](?:\[(?:LOCAL|CLOUD)\])?\s+(?P<id>AV-G-[A-Z0-9]+)\b",
)
INDEX_OPEN = re.compile(
    r"^\|\s*(?P<id>AV-G-[A-Z0-9]+)\s*\|[^|]*\|\s*(?P<status>🔲|❌)\s*\|",
)


def parse_gaps(text: str) -> tuple[set[str], set[str]]:
    open_ids: set[str] = set()
    closed_ids: set[str] = set()
    for line in text.splitlines():
        m = GAP_LINE.match(line.strip())
        if not m:
            continue
        gid = m.group("id")
        if m.group("mark").lower() == "x":
            closed_ids.add(gid)
        else:
            open_ids.add(gid)
    return open_ids, closed_ids


def parse_plan(text: str) -> tuple[set[str], set[str]]:
    open_ids: set[str] = set()
    done_ids: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        m = OPEN_PLAN.match(stripped)
        if m:
            open_ids.add(m.group("id"))
            continue
        m = DONE_PLAN.match(stripped)
        if m:
            done_ids.add(m.group("id"))
            continue
        m = INDEX_OPEN.match(stripped)
        if m:
            open_ids.add(m.group("id"))
    return open_ids, done_ids


def check(root: Path) -> list[str]:
    errors: list[str] = []
    gaps_path = root / GAPS_REL
    plan_path = root / PLAN_REL
    if not gaps_path.is_file():
        return [f"MISSING: {GAPS_REL.as_posix()}"]
    if not plan_path.is_file():
        return [f"MISSING: {PLAN_REL.as_posix()}"]

    gap_open, gap_closed = parse_gaps(gaps_path.read_text(encoding="utf-8"))
    plan_open, plan_done = parse_plan(plan_path.read_text(encoding="utf-8"))

    if not gap_open and not gap_closed:
        errors.append(f"{GAPS_REL.as_posix()}: no AV-G-* checklist lines found")

    for gid in sorted(gap_open):
        if gid not in plan_open:
            errors.append(f"open gap {gid} missing open BUILD_PLAN row (🔲/❌)")

    for gid in sorted(gap_closed):
        if gid in plan_open:
            errors.append(f"closed gap {gid} still has open BUILD_PLAN row")

    for gid in sorted(plan_open):
        if gid not in gap_open and gid not in gap_closed:
            errors.append(f"BUILD_PLAN open {gid} missing from {GAPS_REL.as_posix()}")
        elif gid in gap_closed:
            errors.append(f"BUILD_PLAN open {gid} but gaps file marks [x]")

    # Closed gaps may be archived (no ✅ row left); that is OK.
    _ = plan_done
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args(argv)
    errors = check(args.root.resolve())
    if errors:
        print("Avalonia gap sync FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Avalonia gap sync OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
