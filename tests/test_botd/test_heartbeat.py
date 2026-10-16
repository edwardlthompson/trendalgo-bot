"""H5 heartbeat: a silent host raises one alert on the injected channel; the owner picks the channel."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.botd.heartbeat import MIN_MAX_GAP_S, Heartbeat
from trendalgo.botd.host_store import HostStore

START = 1_800_000_000


def _heartbeat(tmp_path: Path, max_gap_s: int = 300) -> Heartbeat:
    return Heartbeat(HostStore(tmp_path / "host.db"), max_gap_s=max_gap_s)


def test_the_last_beat_is_recorded_and_updated(tmp_path: Path) -> None:
    beat = _heartbeat(tmp_path)
    assert beat.last_beat() is None
    beat.beat(START)
    beat.beat(START + 60)
    assert beat.last_beat() == START + 60


def test_no_alert_while_the_host_beats_within_the_gap(tmp_path: Path) -> None:
    beat = _heartbeat(tmp_path)
    beat.beat(START)
    sent: list[str] = []
    assert beat.check(START + 300, started_at=START, notify=sent.append) is False
    assert sent == []


def test_a_silent_host_raises_one_alert_naming_the_gap_and_limit(tmp_path: Path) -> None:
    beat = _heartbeat(tmp_path)
    beat.beat(START)
    sent: list[str] = []
    assert beat.check(START + 301, started_at=START, notify=sent.append) is True
    assert sent == ["TrendAlgo host silent for 301 s (limit 300 s)"]


def test_a_host_that_never_beats_is_measured_from_its_start(tmp_path: Path) -> None:
    beat = _heartbeat(tmp_path)
    sent: list[str] = []
    assert beat.check(START + 200, started_at=START, notify=sent.append) is False
    assert beat.check(START + 301, started_at=START, notify=sent.append) is True
    assert len(sent) == 1


def test_the_gap_must_be_at_least_the_minimum(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least"):
        _heartbeat(tmp_path, max_gap_s=MIN_MAX_GAP_S - 1)
