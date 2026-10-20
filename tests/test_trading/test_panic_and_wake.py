"""Phase 0: panic halt, wake paused, safety lights, live alerts."""

from __future__ import annotations

from pathlib import Path

from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.trading.live_order_alert import LiveOrderAttempt, notify_live_order_attempt
from trendalgo.trading.order_journal import OrderJournal
from trendalgo.trading.panic import run_panic
from trendalgo.trading.safety_lights import LightState, compute_safety_lights
from trendalgo.trading.wake_policy import pause_all_bots_on_wake


def test_panic_halts_and_pauses_bots(tmp_path: Path) -> None:
    orch = BotOrchestrator(tmp_path / "bots.db")
    bot_id = orch.add_bot("A", "sma", "BTC/USD", equity_usd=100, enabled=True)
    journal = OrderJournal(tmp_path / "journal.db")
    flatten: list[tuple[str, str]] = []
    result = run_panic(
        guard=journal,
        orchestrator=orch,
        post_flatten=lambda a, b: flatten.append((a, b)),
        reason="test_panic",
    )
    assert journal.is_halted("kraken")
    assert bot_id in result.paused_bots
    assert orch.get_bot(bot_id)["enabled"] is False
    assert flatten == [("flatten", "A")]


def test_wake_pauses_enabled_bots(tmp_path: Path) -> None:
    orch = BotOrchestrator(tmp_path / "bots.db")
    a = orch.add_bot("A", "sma", "BTC/USD", equity_usd=100, enabled=True)
    b = orch.add_bot("B", "sma", "ETH/USD", equity_usd=100, enabled=False)
    paused = pause_all_bots_on_wake(orch)
    assert a in paused
    assert b not in paused
    assert orch.get_bot(a)["enabled"] is False


def test_safety_lights_keys_are_not_live() -> None:
    lights = compute_safety_lights(
        vault_unlocked=True,
        has_query_key=True,
        sync_ok=True,
        go_live_approved=False,
    )
    assert lights.vault == LightState.OK
    assert lights.sync == LightState.OK
    assert lights.live == LightState.OFF


def test_live_order_alert_skips_dry_run() -> None:
    seen: list[tuple[str, str]] = []
    attempt = LiveOrderAttempt(
        exchange="kraken", pair="BTC/USD", side="buy", amount=0.01, dry_run=True
    )
    assert notify_live_order_attempt(attempt, lambda t, b: seen.append((t, b))) is False
    assert seen == []
    live = LiveOrderAttempt(
        exchange="kraken", pair="BTC/USD", side="buy", amount=0.01, dry_run=False
    )
    assert notify_live_order_attempt(live, lambda t, b: seen.append((t, b))) is True
    assert len(seen) == 1
