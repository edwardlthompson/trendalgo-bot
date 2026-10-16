"""Wizard state: steps finish in order, a failed check does not move the step, and saves need the lock."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trendalgo.device.lock import ProfileLock
from trendalgo.device.profile import ProfileError
from trendalgo.device.wizard.state import (
    STEP_IDS,
    WizardError,
    WizardState,
    advance,
    load_state,
    save_state,
)
from trendalgo.device.wizard.validators import Problem

PROBLEM = Problem("step.not_acknowledged", "Tick the box.")


def test_a_fresh_profile_starts_at_the_first_step(tmp_path: Path) -> None:
    state = load_state(tmp_path / "wizard.json")
    assert state == WizardState()
    assert state.next_step() == STEP_IDS[0] == "W0"


def test_steps_finish_in_order_and_the_last_one_ends_the_list() -> None:
    state = WizardState()
    for step_id in STEP_IDS:
        state = state.complete(step_id)
    assert state.done == STEP_IDS
    assert state.next_step() is None


def test_a_step_out_of_order_is_refused() -> None:
    with pytest.raises(WizardError, match="W2 is not the next step"):
        WizardState().complete("W2")


def test_a_failed_check_leaves_the_step_where_it_was() -> None:
    state, problems = advance(WizardState(), "W0", [PROBLEM])
    assert state == WizardState()
    assert problems == [PROBLEM]


def test_a_passed_check_finishes_the_step() -> None:
    state, problems = advance(WizardState(), "W0", [])
    assert problems == []
    assert state.done == ("W0",)
    assert state.next_step() == "W1"


def test_the_state_round_trips_under_the_profile_lock(tmp_path: Path) -> None:
    path = tmp_path / "wizard.json"
    lock = ProfileLock(tmp_path / "device.lock")
    lock.acquire()
    try:
        state = WizardState(("W0", "W1"))
        save_state(path, state, lock)
        assert load_state(path) == state
    finally:
        lock.release()


def test_saving_without_the_profile_lock_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "wizard.json"
    with pytest.raises(WizardError, match="profile lock must be held"):
        save_state(path, WizardState(("W0",)), ProfileLock(tmp_path / "device.lock"))
    assert not path.exists()


def test_the_lock_reports_whether_this_object_holds_it(tmp_path: Path) -> None:
    lock = ProfileLock(tmp_path / "device.lock")
    assert lock.held is False
    lock.acquire()
    assert lock.held is True
    lock.release()
    assert lock.held is False


def test_the_state_file_holds_step_ids_and_nothing_else(tmp_path: Path) -> None:
    path = tmp_path / "wizard.json"
    lock = ProfileLock(tmp_path / "device.lock")
    lock.acquire()
    try:
        save_state(path, WizardState(("W0", "W1")), lock)
    finally:
        lock.release()
    assert json.loads(path.read_text(encoding="utf-8")) == {"done": ["W0", "W1"]}


def test_a_corrupt_state_file_is_refused_and_never_replaced(tmp_path: Path) -> None:
    path = tmp_path / "wizard.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ProfileError, match="Move it aside"):
        load_state(path)
    assert path.read_text(encoding="utf-8") == "{not json"


def test_a_state_file_that_is_not_an_object_is_refused_and_never_replaced(tmp_path: Path) -> None:
    path = tmp_path / "wizard.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ProfileError, match="must hold a JSON object"):
        load_state(path)
    assert path.read_text(encoding="utf-8") == "[1, 2]"


@pytest.mark.parametrize(
    ("done", "message"),
    [
        (["W1"], "out of order"),
        (["W0", "W2"], "out of order"),
        ("W0", "no list of finished steps"),
        ([1], "no list of finished steps"),
    ],
)
def test_steps_that_are_out_of_order_or_malformed_are_refused(
    tmp_path: Path, done: object, message: str
) -> None:
    path = tmp_path / "wizard.json"
    path.write_text(json.dumps({"done": done}), encoding="utf-8")
    with pytest.raises(ProfileError, match=message):
        load_state(path)
