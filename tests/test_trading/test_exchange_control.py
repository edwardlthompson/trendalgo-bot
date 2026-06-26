"""S16 per-exchange pause and go-live tests."""

from __future__ import annotations

from pathlib import Path

from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.multi_exchange import route_order


def test_pause_blocks_live_route(tmp_path: Path) -> None:
    control = ExchangeControlStore(tmp_path / "control.db")
    control.set_paused("kraken", True)
    try:
        route_order("kraken", "BTC/USD", "buy", 10.0, dry_run=False, control=control)
        raise AssertionError("expected pause block")
    except ValueError as exc:
        assert "exchange_paused" in str(exc)


def test_go_live_required_for_live(tmp_path: Path) -> None:
    control = ExchangeControlStore(tmp_path / "control.db")
    try:
        route_order("gemini", "BTC/USD", "buy", 10.0, dry_run=False, control=control)
        raise AssertionError("expected go-live block")
    except ValueError as exc:
        assert "go_live_required" in str(exc)


def test_go_live_approval_allows_dry_run_while_live_blocked(tmp_path: Path) -> None:
    control = ExchangeControlStore(tmp_path / "control.db")
    control.approve_go_live("binanceus")
    result = route_order("binanceus", "BTC/USD", "buy", 10.0, dry_run=True, control=control)
    assert result["status"] == "simulated"
