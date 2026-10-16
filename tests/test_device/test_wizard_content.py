"""Wizard content: the shipped steps pass lint, the lint refuses bad shapes, and the guide matches."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from trendalgo.device.wizard import guide
from trendalgo.device.wizard.content import STEPS
from trendalgo.device.wizard.lint import lint
from trendalgo.device.wizard.model import Source, Step

CHECKED = date(2026, 10, 10)


def _step(step_id: str) -> Step:
    return next(step for step in STEPS if step.step_id == step_id)


def _swap(step_id: str, **changes: object) -> list[Step]:
    return [replace(step, **changes) if step.step_id == step_id else step for step in STEPS]


def test_the_shipped_content_passes_lint() -> None:
    assert lint(STEPS) == []


def test_the_guide_on_disk_matches_the_content() -> None:
    assert guide.main(["--check"]) == 0


def test_every_source_is_listed_with_its_check_date() -> None:
    text = guide.render_guide(STEPS)
    for step in STEPS:
        for source in step.sources:
            assert f"[{source.label}]({source.url}), checked {source.verified.isoformat()}" in text


def test_a_hand_edit_to_the_guide_fails_the_drift_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "SETUP_GUIDE.md"
    monkeypatch.setattr(guide, "GUIDE_PATH", path)
    path.write_text(guide.render_guide(STEPS) + "An edit nobody made in the content.\n", "utf-8")
    assert guide.main(["--check"]) == 1
    assert guide.main(["--write"]) == 0
    assert guide.main(["--check"]) == 0


def test_a_missing_guide_fails_the_drift_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(guide, "GUIDE_PATH", tmp_path / "SETUP_GUIDE.md")
    assert guide.main(["--check"]) == 1


@pytest.mark.parametrize(
    "sentence",
    [
        "Enter your Kraken password so the wizard can log in.",
        "Type your seed phrase to confirm the host.",
        "Provide the card number used for billing.",
        "Send us the withdrawal address for payouts.",
    ],
)
def test_asking_for_a_secret_is_refused(sentence: str) -> None:
    steps = _swap("W0", body=_step("W0").body + (sentence,))
    assert any("asks for a secret" in problem for problem in lint(steps))


def test_a_warning_that_names_a_secret_is_allowed() -> None:
    steps = _swap("W0", body=_step("W0").body + ("Never share your password or seed phrase.",))
    assert lint(steps) == []


def test_a_plain_http_source_is_refused() -> None:
    source = Source("Oracle Cloud Free Tier", "http://www.oracle.com/cloud/free/", CHECKED)
    assert any("must use https" in problem for problem in lint(_swap("W3", sources=(source,))))


def test_a_source_off_the_official_list_is_refused() -> None:
    source = Source("Forum post", "https://example.com/oracle-free", CHECKED)
    problems = lint(_swap("W3", sources=(source,)))
    assert any("not on the official list" in problem for problem in problems)


def test_a_provider_step_without_a_source_is_refused() -> None:
    assert any("need a source" in problem for problem in lint(_swap("W3", sources=())))


@pytest.mark.parametrize("phrase", ["home region", "24 hours", "12 GB", "Path B", "static"])
def test_w3_keeps_its_required_wording(phrase: str) -> None:
    body = tuple(paragraph.replace(phrase, "[removed]") for paragraph in _step("W3").body)
    problems = lint(_swap("W3", body=body))
    assert any(phrase in problem for problem in problems)


def test_w1_keeps_the_withdraw_permission_warning() -> None:
    body = tuple(p.replace("Withdraw Funds", "[removed]") for p in _step("W1").body)
    assert any("Withdraw Funds" in problem for problem in lint(_swap("W1", body=body)))


def test_a_duplicate_step_id_is_refused() -> None:
    assert any("duplicate step id" in problem for problem in lint([*STEPS, _step("W1")]))


def test_a_required_step_cannot_be_dropped() -> None:
    steps = [step for step in STEPS if step.step_id != "W4"]
    assert any("W4: step is missing" in problem for problem in lint(steps))
