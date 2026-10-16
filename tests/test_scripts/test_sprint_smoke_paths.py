"""Sprint smoke path checks: non-path tokens are skipped; removed paths must be absent."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from sprint_smoke_map import backtick_paths, split_task_paths  # noqa: E402
from sprint_smoke_probes import probe_docs, probe_docs_absent  # noqa: E402


def test_http_routes_are_not_repo_paths() -> None:
    task = "Routes `GET /api/v1/status`, `PUT /api/v1/plan`, and `POST /api/v1/pair`."
    assert backtick_paths(task) == []


def test_urls_templates_and_globs_are_not_repo_paths() -> None:
    task = (
        "Targets `http://127.0.0.1:<port>`, `tests/test_device/test_wizard_*.py`, "
        "and `scripts/dev-local.*`."
    )
    assert backtick_paths(task) == []


def test_slash_commands_and_host_paths_are_not_repo_paths() -> None:
    task = r"Run `/gates` with `~/.local/bin` or `C:\Users\me\tools` present."
    assert backtick_paths(task) == []


def test_repo_paths_are_kept_in_order() -> None:
    task = "Files `src/trendalgo/botd/`, `docs/SETUP_GUIDE.md`, and `TEMPLATE_INDEX.json`."
    assert backtick_paths(task) == [
        "src/trendalgo/botd/",
        "docs/SETUP_GUIDE.md",
        "TEMPLATE_INDEX.json",
    ]


def test_scope_paths_must_exist_when_the_row_deletes_nothing() -> None:
    task = "`p1` Adds the loop. Tests: `tests/test_x.py`. — scope: `src/trendalgo/x/`"
    present, gone = split_task_paths(task)
    assert present == ["tests/test_x.py", "src/trendalgo/x/"]
    assert gone == []


def test_removed_clause_and_delete_scope_are_expected_absent() -> None:
    task = (
        "`p7` Delete old files. Removed `examples/web/`, `.github/workflows/pages.yml`, "
        "and `scripts/dev-local.*`. Kept `docs/x.md`. — scope: `examples/web/`"
    )
    present, gone = split_task_paths(task)
    assert present == ["docs/x.md"]
    assert gone == ["examples/web/", ".github/workflows/pages.yml"]


def test_removed_function_name_does_not_make_a_removal_row() -> None:
    task = (
        "`p8` Removed: `license_fee_for_trade` function. Tests: `tests/test_fee.py`. "
        "— scope: `src/trendalgo/billing/`"
    )
    present, gone = split_task_paths(task)
    assert gone == []
    assert present == ["tests/test_fee.py", "src/trendalgo/billing/"]


def test_names_with_no_repo_top_folder_are_not_checked(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("ok\n", encoding="utf-8")
    assert probe_docs(tmp_path, ["TrendAlgo/practice-secret", "docs/a.md"]).ok


def test_missing_repo_path_fails_the_docs_probe(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    assert not probe_docs(tmp_path, ["docs/gone.md"]).ok


def test_bare_file_names_are_found_under_src(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "vendor_manifest.json").write_text("{}\n", encoding="utf-8")
    assert probe_docs(tmp_path, ["vendor_manifest.json"]).ok


def test_removed_paths_fail_while_they_still_exist(tmp_path: Path) -> None:
    (tmp_path / "examples" / "web").mkdir(parents=True)
    assert not probe_docs_absent(tmp_path, ["examples/web/"]).ok
    (tmp_path / "examples" / "web").rmdir()
    assert probe_docs_absent(tmp_path, ["examples/web/"]).ok
