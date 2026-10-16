"""Tests for the founder gate CLI helpers (scripts/founder_gate.py)."""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("founder_gate", ROOT / "scripts" / "founder_gate.py")
assert _SPEC is not None and _SPEC.loader is not None
founder_gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(founder_gate)


def test_hard_gates_match_build_plan() -> None:
    assert founder_gate.HARD_GATES == frozenset(
        {"H-006", "H-008", "H-010", "H-011", "H-023", "H-028", "H-031", "H-032", "H-036"}
    )


def test_repo_path_becomes_root_relative_posix() -> None:
    script = founder_gate.ROOT / "scripts" / "verify-branch-protection.sh"
    assert founder_gate._repo_relative_args([str(script), "--quick"]) == [
        "scripts/verify-branch-protection.sh",
        "--quick",
    ]


def test_path_outside_repo_is_unchanged() -> None:
    outside = founder_gate.ROOT.parent / "elsewhere" / "x.sh"
    assert founder_gate._repo_relative_args([str(outside)]) == [str(outside)]


def test_plain_arguments_are_unchanged() -> None:
    assert founder_gate._repo_relative_args(["--quick", "origin"]) == ["--quick", "origin"]


def test_run_returns_exit_code_and_output() -> None:
    code, text = founder_gate._run([sys.executable, "-c", "print('hello'); raise SystemExit(3)"])
    assert code == 3
    assert text == "hello"


def test_missing_command_is_reported_not_raised() -> None:
    code, text = founder_gate._run(["trendalgo-no-such-command-xyz"])
    assert code == 1
    assert text


def test_timeout_returns_even_when_a_grandchild_keeps_output_open() -> None:
    # The grandchild inherits the child's stdout: the shape that could hang a pipe-based runner.
    # Keep sleeps short so a missed kill cannot stall CI for minutes.
    child = (
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(8)'])\n"
        "time.sleep(8)\n"
    )
    started = time.monotonic()
    code, text = founder_gate._run([sys.executable, "-c", child], timeout=1)
    assert code == 1
    assert "timed out" in text
    assert time.monotonic() - started < 15


def test_sprint_scope_stops_at_reentry(monkeypatch) -> None:
    # sprint-preflight.sh calls back into preflight-sprint, which calls this function again.
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> tuple[int, str]:
        calls.append(cmd)
        return 0, "unexpected"

    monkeypatch.setattr(founder_gate, "_run", fake_run)
    monkeypatch.setenv(founder_gate.SPRINT_PREFLIGHT_GUARD, "12")
    code, msg = founder_gate.preflight_sprint_scope(12)
    assert code == 2
    assert "re-entry" in msg
    assert calls == []


def test_sprint_scope_sets_guard_for_child_and_restores_it(monkeypatch) -> None:
    seen: list[str | None] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> tuple[int, str]:
        seen.append(os.environ.get(founder_gate.SPRINT_PREFLIGHT_GUARD))
        return 0, "scope checked"

    monkeypatch.setattr(founder_gate, "_run", fake_run)
    monkeypatch.delenv(founder_gate.SPRINT_PREFLIGHT_GUARD, raising=False)
    assert founder_gate.preflight_sprint_scope(12) == (0, "scope checked")
    assert seen == ["12"]
    assert founder_gate.SPRINT_PREFLIGHT_GUARD not in os.environ
