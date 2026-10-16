"""Render docs/SETUP_GUIDE.md from the wizard content (W-LABEL).

`--write` regenerates the guide. `--check` exits 1 when the guide differs from the content, so a
hand edit to the guide fails the drift check. Both refuse to run while the content fails lint.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from trendalgo.device.wizard.content import STEPS
from trendalgo.device.wizard.lint import lint
from trendalgo.device.wizard.model import Step

ROOT = Path(__file__).resolve().parents[4]
GUIDE_PATH = ROOT / "docs" / "SETUP_GUIDE.md"
HEADER = (
    "# TrendAlgo setup guide",
    "",
    "<!-- Generated from src/trendalgo/device/wizard/content.py. Edit that file, then run "
    "`python -m trendalgo.device.wizard.guide --write`. -->",
    "",
)


def render_guide(steps: Sequence[Step]) -> str:
    """Markdown for the guide: one section per step, with its sources and their check dates."""
    lines: list[str] = list(HEADER)
    for step in steps:
        lines.extend([f"## {step.step_id}: {step.title}", ""])
        for paragraph in step.body:
            lines.extend([paragraph, ""])
        if step.sources:
            lines.extend(["Sources:", ""])
            lines.extend(
                f"- [{source.label}]({source.url}), checked {source.verified.isoformat()}"
                for source in step.sources
            )
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wizard-guide", description="Setup guide from the content"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate docs/SETUP_GUIDE.md")
    mode.add_argument("--check", action="store_true", help="exit 1 if the guide has drifted")
    args = parser.parse_args(argv)
    problems = lint(STEPS)
    if problems:
        print("\n".join(problems))
        return 1
    text = render_guide(STEPS)
    if args.write:
        GUIDE_PATH.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {GUIDE_PATH.name}")
        return 0
    current = GUIDE_PATH.read_text(encoding="utf-8") if GUIDE_PATH.is_file() else ""
    if current != text:
        print(f"{GUIDE_PATH.name} differs from the wizard content; run with --write")
        return 1
    print(f"{GUIDE_PATH.name} matches the wizard content")
    return 0


if __name__ == "__main__":
    sys.exit(main())
