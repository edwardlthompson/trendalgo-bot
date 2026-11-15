#!/usr/bin/env python3
"""Ensure README Exchange support table matches support_matrix.json.

Usage:
  python scripts/check-support-matrix-readme.py
  python scripts/check-support-matrix-readme.py --write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _ensure_path() -> None:
    src = ROOT / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    _ensure_path()
    from trendalgo.device.support_matrix_readme import (
        END,
        START,
        extract_marked_block,
        render_exchange_support_table,
    )

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    expected = render_exchange_support_table().strip()
    if args.write:
        if START not in text or END not in text:
            raise SystemExit(f"README missing markers {START!r} / {END!r}")
        before, rest = text.split(START, 1)
        _old, after = rest.split(END, 1)
        readme.write_text(
            before + START + "\n\n" + expected + "\n\n" + END + after,
            encoding="utf-8",
        )
        print(f"updated {readme}")
        return 0
    inner = extract_marked_block(text)
    if inner is None:
        print("FAIL: README missing support-matrix markers", file=sys.stderr)
        return 1
    if inner.strip() != expected:
        print("FAIL: README Exchange table drifts from support_matrix.json", file=sys.stderr)
        return 1
    print("OK: README Exchange table matches support_matrix.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
