"""Unit tests for command parsing."""

from __future__ import annotations

import pytest

from trendalgo.botd.commands import parse_command


def test_parse_command_ok() -> None:
    action, bot_id, key = parse_command(
        {"action": "Flatten", "bot_id": "b1", "idempotency_key": "k1"}
    )
    assert action == "flatten"
    assert bot_id == "b1"
    assert key == "k1"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"action": "pause"},
        {"action": "pause", "bot_id": "b1"},
        {"action": "nope", "bot_id": "b1", "idempotency_key": "k"},
    ],
)
def test_parse_command_rejects_bad(body: dict) -> None:
    with pytest.raises(ValueError):
        parse_command(body)
