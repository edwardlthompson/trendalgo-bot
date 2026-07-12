"""Unit tests for TradingView → order bridge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.signals.runner_bridge import bridge_tradingview_signal
from trendalgo.trading.control import ExchangeControlStore


class _Bot:
    dry_run = True


class _State:
    def __init__(self, tmp_path: Path) -> None:
        self.portfolio_store = PortfolioStore(tmp_path / "p.db")
        self.exchange_control = ExchangeControlStore(tmp_path / "ctl.db")
        self.bot = _Bot()
        self.logs: list[str] = []

    def log(self, message: str) -> None:
        self.logs.append(message)


def test_bridge_log_only_without_ack(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.delenv("TV_EXECUTION_ACK", raising=False)
    state = _State(tmp_path)
    result = bridge_tradingview_signal(
        {"pair": "BTC/USD", "action": "buy", "amount_usd": 10},
        state,
    )
    assert result == {"status": "log_only", "executed": False}
    assert any("log-only" in line for line in state.logs)


def test_bridge_executes_when_acked(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("TV_EXECUTION_ACK", "1")
    state = _State(tmp_path)

    def _fake_route(
        exchange: str,
        pair: str,
        action: str,
        amount: float,
        *,
        dry_run: bool,
        control: Any,
    ) -> dict[str, Any]:
        del control
        return {
            "pair": pair,
            "mode": "dry_run" if dry_run else "live",
            "order_id": "ord-1",
            "exchange_id": exchange,
            "action": action,
            "amount_usd": amount,
        }

    monkeypatch.setattr("trendalgo.signals.runner_bridge.route_order", _fake_route)
    result = bridge_tradingview_signal(
        {"pair": "ETH/USD", "action": "long", "amount_usd": 25, "exchange_id": "kraken"},
        state,
    )
    assert result["executed"] is True
    assert result["status"] == "executed"
    assert result["tick"]["action"] == "buy"
    assert result["tick"]["order_id"] == "ord-1"


def test_bridge_rejects_invalid_signal(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("TV_EXECUTION_ACK", "1")
    state = _State(tmp_path)
    result = bridge_tradingview_signal({"pair": "", "action": "hold"}, state)
    assert result["executed"] is False
    assert result["status"] == "failed"
    assert "pair" in result["error"].lower() or "action" in result["error"].lower()
