from pathlib import Path

from trendalgo.backtest.library import BacktestLibrary
from trendalgo.backtest.slippage import apply_slippage
from trendalgo.api.backtest_runner import run_sample_backtest
from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.risk.sizing import atr_stake_size
from trendalgo.signals.generic import GenericSignalWebhook
from trendalgo.templates.import_export import export_json, import_json
from trendalgo.watchlist.store import WatchlistStore


def test_template_export_import() -> None:
    raw = export_json("smart-dca", {"dca_amount_usd": 100})
    tpl = import_json(raw)
    assert tpl.id == "smart-dca"
    assert tpl.param_values["dca_amount_usd"] == 100


def test_backtest_library_clone(tmp_path: Path) -> None:
    lib = BacktestLibrary(tmp_path / "lib.db")
    run_id = lib.save("smart-dca", "BTC/USD", {"metrics": {"sharpe_ratio": 1.2}})
    clone_id = lib.clone(run_id, "v2")
    assert clone_id != run_id
    assert len(lib.list_runs()) == 2


def test_slippage_reduces_profit() -> None:
    base = run_sample_backtest(strategy="x", pair="BTC/USD", timeframe="5m", timerange="20240101")
    adj = apply_slippage(base, 0.01, 0.01)
    assert adj.profit_total < base.profit_total


def test_bot_orchestrator_add(tmp_path: Path) -> None:
    orch = BotOrchestrator(tmp_path / "bots.db")
    orch.add_bot("Bot-2", "grid-trading", "ETH/USD")
    bots = orch.list_bots()
    assert len(bots) >= 2


def test_watchlist_alert(tmp_path: Path) -> None:
    store = WatchlistStore(tmp_path / "wl.db")
    store.add("ETH/USD", 0.05, 50)
    msg = store.check_price_move("ETH/USD", 0.06)
    assert msg is not None


def test_generic_webhook() -> None:
    handler = GenericSignalWebhook(secret="")
    result = handler.handle(b'{"pair":"BTC/USD","action":"buy"}')
    assert result.accepted
    secured = GenericSignalWebhook(secret="testsecret")
    bad = secured.handle(b'{"pair":"BTC/USD","action":"buy"}', signature="bad")
    assert not bad.accepted


def test_atr_sizing() -> None:
    stake = atr_stake_size(1000, 0.02)
    assert 10 <= stake <= 500


def test_market_event_and_attribution() -> None:
    from trendalgo.alerts.market_events import evaluate_market_event
    from trendalgo.backtest.attribution import attribute_signals
    from trendalgo.backtest.compare import compare_runs
    from trendalgo.backtest.hyperopt import trigger_hyperopt

    evt = evaluate_market_event("BTC/USD", 0.04, 1.0)
    assert evt and evt["type"] == "price_move"
    attr = attribute_signals({"profit_total": 100})
    assert attr["lts_contribution_usd"] > 0
    cmp = compare_runs([{"id": 1, "metrics": {"sharpe_ratio": 1}}, {"id": 2, "metrics": {"sharpe_ratio": 2}}])
    assert cmp["winner"] == 2
    job = trigger_hyperopt("smart-dca", "BTC/USD")
    assert job["status"] == "queued"
