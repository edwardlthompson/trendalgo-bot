#!/usr/bin/env python3
"""Archive fully-complete BUILD_PLAN sprints to COMPLETED_TASKS.md.

Removes checked-off sprint detail blocks from the active board and keeps a
one-line summary in the Completed table + Archived Sprints row.

Usage:
  python scripts/archive-build-plan-sprint.py [--dry-run] [--sprint S19]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_PLAN = ROOT / "BUILD_PLAN.md"
COMPLETED = ROOT / "COMPLETED_TASKS.md"

SPRINT_HEADER = re.compile(r"^### Sprint (\S+) — (.+?)(?:\s+✅)?\s*$")
TASK_DONE = re.compile(r"^\d+\.\s+✅")
TASK_OPEN = re.compile(r"^\d+\.\s+(?:🔲|❌)")
ACTIVE_HEADER = re.compile(r"^## Active — (.+)$")


@dataclass
class SprintBlock:
    sprint_id: str
    title: str
    start: int
    end: int
    lines: list[str]
    complete: bool


def _find_sprint_blocks(lines: list[str]) -> list[SprintBlock]:
    blocks: list[SprintBlock] = []
    i = 0
    while i < len(lines):
        match = SPRINT_HEADER.match(lines[i])
        if not match:
            i += 1
            continue
        sprint_id, title = match.group(1), match.group(2).strip()
        start = i
        i += 1
        while i < len(lines):
            if lines[i].startswith("### ") or (
                lines[i].startswith("## ") and not lines[i].startswith("### ")
            ):
                break
            i += 1
        block_lines = lines[start:i]
        has_tasks = any(TASK_DONE.match(line) or TASK_OPEN.match(line) for line in block_lines)
        has_open = any(TASK_OPEN.match(line) for line in block_lines)
        complete = has_tasks and not has_open
        blocks.append(
            SprintBlock(
                sprint_id=sprint_id,
                title=title,
                start=start,
                end=i,
                lines=block_lines,
                complete=complete,
            )
        )
    return blocks


def _format_completed_section(block: SprintBlock, archived_on: str) -> str:
    rows: list[str] = [
        f"## Sprint {block.sprint_id} — {block.title} ({archived_on})",
        "",
    ]
    for line in block.lines[1:]:
        stripped = line.strip()
        if not stripped:
            rows.append("")
            continue
        if TASK_DONE.match(line):
            rows.append(f"- {line.strip()}")
        elif line.startswith("**Exit:**"):
            rows.append(f"- {stripped}")
        elif line.startswith("**Blocks:**"):
            rows.append(f"- {stripped}")
    rows.append("")
    return "\n".join(rows)


def _completed_has_sprint(text: str, sprint_id: str) -> bool:
    needle = f"## Sprint {sprint_id} —"
    return needle in text


def _insert_completed(text: str, section: str) -> str:
    marker = "> Archive of finished BUILD_PLAN items."
    if marker not in text:
        return section + text
    idx = text.index(marker) + len(marker)
    while idx < len(text) and text[idx] in "\r\n":
        idx += 1
    return text[:idx] + "\n\n" + section + text[idx:]


def _update_active_header(line: str, archived_ids: set[str]) -> str:
    match = ACTIVE_HEADER.match(line)
    if not match:
        return line
    label = match.group(1)
    parts = re.split(r"\s*\(([^)]+)\)\s*$", label, maxsplit=1)
    if len(parts) < 2:
        return line
    prefix, inner = parts[0].strip(), parts[1]
    tokens = re.split(r"\s*[–—-]\s*", inner)
    archived_norm = {_normalize_sprint_id(a) for a in archived_ids} | archived_ids
    remaining = [
        t.strip()
        for t in tokens
        if t.strip() and _normalize_sprint_id(t.strip()) not in archived_norm
    ]
    if not remaining:
        return line
    if len(remaining) == 1:
        return f"## Active — {prefix} ({remaining[0]})"
    return f"## Active — {prefix} ({remaining[0]}–{remaining[-1]})"


def _next_sprint_label(current: str, next_num: int) -> str:
    """Preserve program name (DEX vs Exchange) when bumping sprint number."""
    match = re.match(r"^(.+?\s+)S\d+$", current.strip())
    if match:
        return f"{match.group(1)}S{next_num}"
    return f"Exchange Program S{next_num}"


def _archived_row_prefix(sprint_id: str) -> str:
    num = re.search(r"(\d+)", sprint_id)
    if num and int(num.group(1)) >= 21:
        return "DEX"
    return "Exchange"


def _update_current_sprint(lines: list[str], archived_ids: set[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if line.startswith("## Current sprint:") and archived_ids:
            match = re.search(r"\*\*([^*]+)\*\*", line)
            if match:
                current = match.group(1)
                for sid in sorted(archived_ids, key=_sprint_sort_key):
                    sid_norm = _normalize_sprint_id(sid)
                    if sid_norm in current or f"S{sid_norm}" in current:
                        num_match = re.search(r"(\d+)", sid_norm)
                        if num_match:
                            n = int(num_match.group(1)) + 1
                            line = re.sub(
                                r"\*\*[^*]+\*\*",
                                f"**{_next_sprint_label(current, n)}**",
                                line,
                                count=1,
                            )
                        break
        out.append(line)
    return out


def _display_sprint_id(sprint_id: str) -> str:
    if sprint_id.startswith(("S", "M", "R-")):
        return sprint_id
    return f"S{sprint_id}"


def _normalize_sprint_id(sprint_id: str) -> str:
    if sprint_id.startswith("S") and sprint_id[1:].isdigit():
        return sprint_id[1:]
    return sprint_id


def _sprint_sort_key(sprint_id: str) -> tuple[int, str]:
    num = re.search(r"(\d+)", sprint_id)
    return (int(num.group(1)) if num else 0, sprint_id)


def _archived_row_exists(text: str, sprint_id: str) -> bool:
    display = _display_sprint_id(sprint_id)
    prefix = _archived_row_prefix(sprint_id)
    return (
        f"| {prefix} {display} |" in text
        or f"| Exchange {display} |" in text
        or f"| Sprint {display} |" in text
    )


def _insert_archived_row(
    lines: list[str], sprint_id: str, title: str, archived_on: str
) -> list[str]:
    if _archived_row_exists("\n".join(lines), sprint_id):
        return lines
    prefix = _archived_row_prefix(sprint_id)
    row = f"| {prefix} {_display_sprint_id(sprint_id)} | {archived_on} | {title} |"
    for i, line in enumerate(lines):
        if line.startswith("| Sprint | Closed |"):
            return lines[: i + 1] + [row] + lines[i + 1 :]
    return lines


def archive_sprints(
    *,
    sprint_filter: str | None = None,
    dry_run: bool = False,
    archived_on: str | None = None,
) -> list[str]:
    if not BUILD_PLAN.is_file():
        raise FileNotFoundError(f"BUILD_PLAN not found: {BUILD_PLAN}")
    if not COMPLETED.is_file():
        raise FileNotFoundError(f"COMPLETED_TASKS not found: {COMPLETED}")

    archived_on = archived_on or date.today().isoformat()
    bp_text = BUILD_PLAN.read_text(encoding="utf-8")
    completed_text = COMPLETED.read_text(encoding="utf-8")
    lines = bp_text.splitlines(keepends=True)
    line_bodies = [ln.rstrip("\r\n") for ln in lines]

    blocks = _find_sprint_blocks(line_bodies)
    targets = [
        b for b in blocks if b.complete and (sprint_filter is None or b.sprint_id == sprint_filter)
    ]
    if sprint_filter and not targets:
        open_match = next((b for b in blocks if b.sprint_id == sprint_filter), None)
        if open_match and not open_match.complete:
            raise SystemExit(f"Sprint {sprint_filter} has open tasks — not archived")
        raise SystemExit(f"Sprint {sprint_filter} not found in BUILD_PLAN.md")

    if not targets:
        return []

    archived_ids = {b.sprint_id for b in targets}
    remove_ranges = sorted(((b.start, b.end) for b in targets), reverse=True)
    new_line_bodies = line_bodies[:]
    for start, end in remove_ranges:
        del new_line_bodies[start:end]

    new_line_bodies = _update_current_sprint(new_line_bodies, archived_ids)
    new_line_bodies = [
        _update_active_header(line, archived_ids) if ACTIVE_HEADER.match(line) else line
        for line in new_line_bodies
    ]

    for block in reversed(targets):
        section = _format_completed_section(block, archived_on)
        if not _completed_has_sprint(completed_text, block.sprint_id):
            completed_text = _insert_completed(completed_text, section)
        new_line_bodies = _insert_archived_row(
            new_line_bodies,
            block.sprint_id,
            block.title,
            archived_on,
        )

    archived_names = [
        f"S{b.sprint_id}" if not b.sprint_id.startswith("S") else b.sprint_id for b in targets
    ]
    if dry_run:
        return archived_names

    BUILD_PLAN.write_text("".join(f"{ln}\n" for ln in new_line_bodies), encoding="utf-8")
    COMPLETED.write_text(completed_text, encoding="utf-8")
    return archived_names


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive complete BUILD_PLAN sprints")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not write files")
    parser.add_argument("--sprint", help="Archive a specific sprint id (e.g. S19 or 19)")
    args = parser.parse_args()
    sprint = args.sprint
    if sprint and sprint.startswith("S") and sprint[1:].isdigit():
        sprint = sprint[1:]
    try:
        archived = archive_sprints(sprint_filter=sprint, dry_run=args.dry_run)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    if not archived:
        print("No fully-complete sprints to archive.")
        return 0
    verb = "Would archive" if args.dry_run else "Archived"
    print(f"{verb}: {', '.join(archived)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
