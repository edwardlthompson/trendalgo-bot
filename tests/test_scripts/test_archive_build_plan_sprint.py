"""Tests for BUILD_PLAN sprint archival script."""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


def _run_script(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    script = repo / "scripts" / "archive-build-plan-sprint.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _mini_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    scripts = repo / "scripts"
    scripts.mkdir()
    src = Path(__file__).resolve().parents[2] / "scripts" / "archive-build-plan-sprint.py"
    shutil.copy2(src, scripts / "archive-build-plan-sprint.py")
    return repo


def test_archives_complete_sprint_only(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    build = repo / "BUILD_PLAN.md"
    done = repo / "COMPLETED_TASKS.md"
    build.write_text(
        textwrap.dedent(
            """
            ## Current sprint: **Exchange Program S19**

            ## Active — Exchange Program (S19–S20)

            ### Sprint 19 — Phase 2 test ✅

            **Exit:** Done things

            1. ✅ [AGENT] Task one
            2. ✅ [AGENT] Task two

            ### Sprint 20 — Next work

            1. 🔲 [AGENT] Open task

            ## Archived sprints

            | Sprint | Closed | Archive |
            |--------|--------|---------|
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    done.write_text("> Archive of finished BUILD_PLAN items.\n", encoding="utf-8")

    result = _run_script(repo)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "S19" in result.stdout
    text = build.read_text(encoding="utf-8")
    assert "### Sprint 19 —" not in text
    assert "### Sprint 20 —" in text
    assert "## Active — Exchange Program (S20)" in text
    completed = done.read_text(encoding="utf-8")
    assert "## Sprint 19 — Phase 2 test" in completed
    assert "Task one" in completed
    assert "| Exchange S19 |" in text


def test_dry_run_leaves_files_unchanged(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    build = repo / "BUILD_PLAN.md"
    done = repo / "COMPLETED_TASKS.md"
    content = (
        textwrap.dedent(
            """
        ## Active — Exchange Program (S19)

        ### Sprint 19 — Done sprint ✅

        1. ✅ [AGENT] Task one
        """
        ).strip()
        + "\n"
    )
    build.write_text(content, encoding="utf-8")
    done.write_text("> Archive of finished BUILD_PLAN items.\n", encoding="utf-8")
    before = build.read_text(encoding="utf-8")
    result = _run_script(repo, "--dry-run")
    assert result.returncode == 0
    assert build.read_text(encoding="utf-8") == before
