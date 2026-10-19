"""One-shot FOSS agent surface: MCP activate + skills-lock install/verify."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = Path(__file__).resolve().parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from activate_cursor_mcp import activate  # noqa: E402
from install_skills_lock import ensure_skills  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--force-mcp", action="store_true", help="Overwrite .cursor/mcp.json")
    p.add_argument(
        "--update-lock",
        action="store_true",
        help="Persist skill hashes / caveman-commit into skills-lock.json",
    )
    args = p.parse_args(argv)
    root = args.root.resolve()
    print("=== activate-cursor-mcp ===")
    rc1 = activate(root, force=args.force_mcp)
    print()
    print("=== install-skills-lock ===")
    rc2 = ensure_skills(root, update_lock=args.update_lock)
    print()
    if rc1 == 0 and rc2 == 0:
        print("OK   activate-cursor-surface finished")
        print(
            "Next: restart Cursor, then confirm MCP tools load (see docs/help/CURSOR_SURFACE.md)."
        )
    return max(rc1, rc2)


if __name__ == "__main__":
    raise SystemExit(main())
