"""An archived sprint (every AGENT row moved to COMPLETED_TASKS.md) still anchors smoke-sprint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from sprint_smoke import run  # noqa: E402
from sprint_smoke_parse import find_sprint, parse_sprints  # noqa: E402

ARCHIVED_BOARD = """# Board

### Sprint S-Demo — archived demo

5. 🔲 [HUMAN] `p0-check` Confirm the console steps — scope: `docs/RISK_REGISTER.md`
"""

OPEN_AGENT_BOARD = """# Board

### Sprint S-Demo — open demo

5. 🔲 [AGENT][LOCAL] `p0-open` Still to build — scope: `docs/RISK_REGISTER.md`
"""


def _args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "sprint": None,
        "require": True,
        "if_complete": False,
        "dry_run": False,
        "with_feature_gate": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_auto_finds_the_newest_header_when_every_agent_row_is_archived() -> None:
    sprint = find_sprint(parse_sprints(ARCHIVED_BOARD), None)
    assert sprint is not None
    assert sprint.title.startswith("Sprint S-Demo")
    assert sprint.agent_auto == []


def test_require_passes_for_an_archived_sprint(tmp_path: Path) -> None:
    (tmp_path / "BUILD_PLAN.md").write_text(ARCHIVED_BOARD, encoding="utf-8")
    assert run(tmp_path, _args()) == 0
    assert run(tmp_path, _args(if_complete=True)) == 0


def test_require_still_fails_while_an_agent_row_is_open(tmp_path: Path) -> None:
    (tmp_path / "BUILD_PLAN.md").write_text(OPEN_AGENT_BOARD, encoding="utf-8")
    assert run(tmp_path, _args()) == 2
