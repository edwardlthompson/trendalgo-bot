"""Import smoke tests for modules with zero or minimal coverage."""

from __future__ import annotations


def test_ai_prompts_constants() -> None:
    from trendalgo.ai import prompts

    assert "Backtest JSON" in prompts.OLLAMA_BACKTEST_USER


def test_lts_backtest_reexport() -> None:
    from trendalgo.lts.backtest import BacktestDataLoader

    assert BacktestDataLoader is not None


def test_trading_adapter_protocol_import() -> None:
    from trendalgo.trading.runner.adapters import base

    assert hasattr(base, "TradingAdapter")


def test_api_main_run(monkeypatch) -> None:
    import sys
    import types

    from trendalgo.api import main

    called: list[tuple[str, ...]] = []

    def fake_uvicorn_run(target: str, *, factory: bool, host: str, port: int) -> None:
        called.append((target, str(factory), host, str(port)))

    monkeypatch.setitem(
        sys.modules,
        "uvicorn",
        types.SimpleNamespace(run=fake_uvicorn_run),
    )
    monkeypatch.setenv("PORT", "9001")
    main.run()
    assert called
    assert called[0][2] == "127.0.0.1"
    assert called[0][3] == "9001"
