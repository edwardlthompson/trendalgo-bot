"""Tests for the founder gate CLI helpers (scripts/founder_gate.py)."""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("founder_gate", ROOT / "scripts" / "founder_gate.py")
assert _SPEC is not None and _SPEC.loader is not None
founder_gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(founder_gate)


def test_hard_gates_match_build_plan() -> None:
    assert founder_gate.HARD_GATES == frozenset(
        {
            "H-006",
            "H-006b",
            "H-008",
            "H-010",
            "H-011",
            "H-023",
            "H-028",
            "H-031",
            "H-032",
            "H-036",
        }
    )


def test_legal_tier_a_gates() -> None:
    assert founder_gate.LEGAL_TIER_A_GATES == frozenset({"H-006", "H-022", "H-023"})


def test_posture_ok_requires_scope_and_date() -> None:
    assert founder_gate._posture_ok("Accepted-scope: owner-only+foss\nAccepted-date: 2026-11-15\n")
    assert not founder_gate._posture_ok("Accepted-scope: owner-only+foss\n")
    assert not founder_gate._posture_ok("Accepted-date: 2026-11-15\n")


def test_legal_approve_note_requires_residual_risk(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(founder_gate, "ROOT", tmp_path)
    (tmp_path / "docs" / "legal-desk" / "counsel").mkdir(parents=True)
    ok, reason = founder_gate._legal_approve_note_ok("H-006", "looks fine")
    assert not ok and "residual-risk" in reason
    ok, reason = founder_gate._legal_approve_note_ok("H-006", "residual-risk owner-only+foss desk")
    assert ok and reason == "ok"


def test_legal_approve_refuses_attorney_approved_without_counsel(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(founder_gate, "ROOT", tmp_path)
    (tmp_path / "docs" / "legal-desk" / "counsel").mkdir(parents=True)
    ok, reason = founder_gate._legal_approve_note_ok(
        "H-006", "residual-risk owner-only+foss attorney approved"
    )
    assert not ok and "attorney approved" in reason


def test_preflight_legal_packet_requires_posture(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(founder_gate, "ROOT", tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "legal-review-packet.md").write_text("packet", encoding="utf-8")
    (tmp_path / "TERMS.md").write_text("terms", encoding="utf-8")
    code, msg = founder_gate.preflight_legal_packet()
    assert code == 1 and "missing" in msg
    posture = docs / "FOUNDER_LEGAL_POSTURE.md"
    posture.write_text("Accepted-scope: owner-only+foss\n", encoding="utf-8")
    code, msg = founder_gate.preflight_legal_packet()
    assert code == 1 and "Accepted-date" in msg
    posture.write_text(
        "Accepted-scope: owner-only+foss\nAccepted-date: 2026-11-15\n",
        encoding="utf-8",
    )
    code, msg = founder_gate.preflight_legal_packet()
    assert code == 2
    assert "Tier A" in msg and "H-006b" in msg


def test_packet_generator_lists_required_adrs() -> None:
    script = (ROOT / "scripts" / "generate-legal-review-packet.sh").read_text(encoding="utf-8")
    for need in (
        "0007-legal-framework",
        "0008-legal-safe-monetization",
        "0017-multi-user-monetization",
        "0018-elastic-license-v2",
        "0020-legal-research-desk",
        "FOUNDER_LEGAL_POSTURE",
        "LEGAL_SAFETY",
    ):
        assert need in script


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


@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="grandchild sleep probe leaves reaped PIDs that stall uv/pytest exit on GHA",
)
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
