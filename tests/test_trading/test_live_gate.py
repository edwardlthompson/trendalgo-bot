"""H2: the host's one live gate. Every combination of inputs has one expected answer."""

from __future__ import annotations

from itertools import product

import pytest

from trendalgo.trading.live_gate import LiveDecision, LiveRequest, decide_live

FULL_LIVE = LiveRequest(
    requested_live=True,
    venue_enabled=True,
    paused=False,
    owner_approved=True,
    credentials_ok=True,
    legal_ack_ok=True,
)


def _expected_allowed(req: LiveRequest) -> bool:
    """Written as a plain rule, independently of the if-chain in decide_live."""
    if req.paused:
        return False
    if not req.requested_live:
        return True
    return req.venue_enabled and req.owner_approved and req.credentials_ok and req.legal_ack_ok


def test_truth_table_matches_the_rule_for_all_64_inputs() -> None:
    for values in product([False, True], repeat=6):
        req = LiveRequest(*values)
        assert decide_live(req).allowed is _expected_allowed(req), req


def test_every_condition_present_is_the_only_live_approval() -> None:
    assert decide_live(FULL_LIVE) == LiveDecision(allowed=True, reason="live_approved")


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("venue_enabled", "venue_not_enabled"),
        ("legal_ack_ok", "legal_ack_missing"),
        ("owner_approved", "go_live_required"),
        ("credentials_ok", "credentials_missing"),
    ],
)
def test_each_missing_live_condition_names_its_refusal(field: str, reason: str) -> None:
    req = LiveRequest(**{**FULL_LIVE.__dict__, field: False})
    assert decide_live(req) == LiveDecision(allowed=False, reason=reason)


def test_pause_refuses_live_and_dry_run_alike() -> None:
    paused_live = LiveRequest(**{**FULL_LIVE.__dict__, "paused": True})
    paused_dry = LiveRequest(**{**paused_live.__dict__, "requested_live": False})
    assert decide_live(paused_live) == LiveDecision(allowed=False, reason="paused")
    assert decide_live(paused_dry) == LiveDecision(allowed=False, reason="paused")


def test_dry_run_needs_no_approval_or_credentials() -> None:
    dry = LiveRequest(
        requested_live=False,
        venue_enabled=False,
        paused=False,
        owner_approved=False,
        credentials_ok=False,
        legal_ack_ok=False,
    )
    assert decide_live(dry) == LiveDecision(allowed=True, reason="dry_run")


def test_the_first_failing_check_names_the_refusal() -> None:
    req = LiveRequest(
        requested_live=True,
        venue_enabled=False,
        paused=False,
        owner_approved=False,
        credentials_ok=False,
        legal_ack_ok=False,
    )
    assert decide_live(req).reason == "venue_not_enabled"
