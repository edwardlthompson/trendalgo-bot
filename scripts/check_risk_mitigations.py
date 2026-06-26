#!/usr/bin/env python3
"""Risk Register Zero — verify and close risks from docs/risk-catalog.json."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "risk-catalog.json"
CLOSED = ROOT / "docs" / "RISK_REGISTER_CLOSED.md"


def _normalize_text(text: str) -> str:
    if "\x00" in text:
        text = text.replace("\x00", "")
    return text


def load_catalog() -> dict:
    if not CATALOG.exists():
        print(f"FAIL missing {CATALOG}", file=sys.stderr)
        sys.exit(1)
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def verify_risk(risk: dict) -> tuple[str, str]:
    """Return PASS, SCHEDULED, or FAIL."""
    status = risk.get("status", "active")
    if status in ("eliminated", "closed", "accepted", "ongoing"):
        return "PASS", f"terminal status={status}"

    check = risk.get("verification")
    if not check:
        return "SCHEDULED", "no verification defined"

    if check.startswith("file:"):
        path = ROOT / check[5:]
        return ("PASS", str(path)) if path.exists() else ("SCHEDULED", f"missing {path}")

    if check.startswith("script:"):
        script = ROOT / check[7:]
        if not script.exists():
            return "SCHEDULED", f"missing {script}"
        if script.suffix == ".py":
            cmd = [sys.executable, str(script)]
        else:
            bash = shutil.which("bash")
            if not bash:
                return "SCHEDULED", f"bash unavailable — {script.name} present"
            cmd = [bash, str(script)]
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = _normalize_text((proc.stdout or "") + (proc.stderr or ""))
        if proc.returncode == 0:
            return "PASS", script.name
        if proc.returncode == 2:
            return "SCHEDULED", proc.stdout.strip() or "scheduled"
        if proc.returncode != 0 and "Windows Subsystem for Linux" in out:
            return "SCHEDULED", f"bash/WSL unavailable — {script.name} present"
        return "FAIL", proc.stderr.strip() or proc.stdout.strip() or "failed"

    return "SCHEDULED", check


def cmd_check(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    risks = catalog["risks"]
    if args.all:
        risks = [r for r in risks if r.get("status") == "active"]
        print(f"Active risks: {len(risks)}")
    elif args.sprint is not None:
        risks = [r for r in risks if r.get("close_sprint") == args.sprint]
    if args.rid:
        risks = [r for r in risks if r["id"] == args.rid]

    worst = 0
    for risk in risks:
        state, msg = verify_risk(risk)
        if args.strict and state == "SCHEDULED" and risk.get("status") == "active":
            if args.sprint is not None and risk.get("close_sprint", 99) <= args.sprint:
                state = "FAIL"
            elif args.all:
                state = "FAIL"
        if state == "FAIL":
            worst = 1
        print(f"{risk['id']}: {state} — {msg}")

    if args.ongoing:
        ongoing = [r for r in catalog["risks"] if r.get("closure_type") == "ongoing"]
        for risk in ongoing:
            state, msg = verify_risk(risk)
            print(f"{risk['id']} (ongoing): {state} — {msg}")
            if args.strict and state == "FAIL":
                worst = 1

    critiques = catalog.get("critiques", [])
    if args.sprint is not None:
        critiques = [c for c in critiques if c.get("close_sprint") == args.sprint]
    elif args.all:
        critiques = [c for c in critiques if c.get("status") == "pending"]
    for critique in critiques:
        state, msg = verify_risk(critique)
        if args.strict and state in ("SCHEDULED", "FAIL") and critique.get("status") == "pending":
            if args.all or (
                args.sprint is not None and critique.get("close_sprint", 99) <= args.sprint
            ):
                state = "FAIL" if state != "PASS" else state
        if state == "FAIL":
            worst = 1
        print(f"{critique['id']}: {state} — {msg}")

    if (
        args.all
        and args.strict
        and len([r for r in catalog["risks"] if r.get("status") == "active"]) > 0
    ):
        worst = 1

    return worst


def cmd_close(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    rid = args.rid
    match = next((r for r in catalog["risks"] if r["id"] == rid), None)
    if not match:
        print(f"Unknown risk {rid}", file=sys.stderr)
        return 1
    state, msg = verify_risk(match)
    if state != "PASS" and not args.force:
        print(f"Cannot close {rid}: {state} — {msg}", file=sys.stderr)
        return 1

    match["status"] = args.closure_type or match.get("closure_type", "closed")
    match["closed_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    match["closed_sprint"] = args.sprint
    if args.note:
        match["close_note"] = args.note

    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    CLOSED.parent.mkdir(parents=True, exist_ok=True)
    line = (
        f"| {rid} | {match.get('title', '')} | {match['status']} | "
        f"S{args.sprint} | {args.note or ''} | {match['closed_at']} |\n"
    )
    if not CLOSED.exists():
        CLOSED.write_text(
            "# Risk Register — Closed\n\n"
            "> Append-only archive.\n\n"
            "| R-ID | Title | Status | Sprint | Note | Closed at |\n"
            "|------|-------|--------|--------|------|----------|\n"
            "\n## Critiques closed\n\n"
            "| C-ID | Critique | Closed sprint | R-IDs |\n"
            "|------|----------|---------------|-------|\n",
            encoding="utf-8",
        )
    text = CLOSED.read_text(encoding="utf-8")
    marker = "\n## Critiques closed"
    if marker in text:
        head, tail = text.split(marker, 1)
        if not head.rstrip().endswith(line.strip()):
            head = head.rstrip() + "\n" + line
        CLOSED.write_text(head + marker + tail, encoding="utf-8")
    else:
        with CLOSED.open("a", encoding="utf-8") as fh:
            fh.write(line)

    print(f"Closed {rid} as {match['status']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--ongoing", action="store_true")
    parser.add_argument("--sprint", type=int, default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("command", nargs="?", default="check", choices=["check", "close"])
    parser.add_argument("rid", nargs="?", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--closure-type", default="")

    args = parser.parse_args()
    if args.command == "close":
        if not args.rid:
            print("Usage: close R-xxx --sprint N", file=sys.stderr)
            return 1
        if args.sprint is None:
            print("--sprint required for close", file=sys.stderr)
            return 1
        return cmd_close(args)
    if args.all:
        args.sprint = None
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
