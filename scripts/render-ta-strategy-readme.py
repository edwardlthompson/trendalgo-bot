#!/usr/bin/env python3
"""Render or check the README All-TA <details> block from ta_strategy_categories.json.

Usage:
  python scripts/render-ta-strategy-readme.py          # print block
  python scripts/render-ta-strategy-readme.py --check  # exit 1 if README markers drift
  python scripts/render-ta-strategy-readme.py --write  # rewrite between markers
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START = "<!-- ta-strategy-categories:start -->"
END = "<!-- ta-strategy-categories:end -->"


def _ensure_path() -> None:
    src = ROOT / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def render_block() -> str:
    _ensure_path()
    from trendalgo.device.ta_strategy_categories import render_readme_strategy_details

    return render_readme_strategy_details()


def readme_inner(text: str) -> str | None:
    if START not in text or END not in text:
        return None
    before, rest = text.split(START, 1)
    _inner, _after = rest.split(END, 1)
    del before
    return _inner.strip("\n")


def write_readme(block: str) -> None:
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"README missing markers {START!r} / {END!r}")
    before, rest = text.split(START, 1)
    _old, after = rest.split(END, 1)
    new = before + START + "\n\n" + block.rstrip() + "\n\n" + END + after
    README.write_text(new, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    block = render_block()
    if args.write:
        write_readme(block)
        print(f"updated {README}")
        return 0
    if args.check:
        text = README.read_text(encoding="utf-8")
        inner = readme_inner(text)
        if inner is None:
            print("FAIL: README missing ta-strategy-categories markers", file=sys.stderr)
            return 1
        if inner.strip() != block.strip():
            print(
                "FAIL: README All-TA details drift from ta_strategy_categories.json",
                file=sys.stderr,
            )
            return 1
        print("OK: README All-TA details match")
        return 0
    sys.stdout.write(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
