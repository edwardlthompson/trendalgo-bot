"""Bot performance credit survives soft-delete."""

from __future__ import annotations

from pathlib import Path

from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.device.bots_performance import performance_rows
from trendalgo.device.scanner_plan_prefill import default_bot_name
from trendalgo.risk.journal import TradeJournal, TradeRecord


def test_default_bot_name_exchange_pair_tf() -> None:
    assert (
        default_bot_name(exchange="Kraken", pair="tia/usd", timeframe="4h") == "Kraken TIA/USD 4h"
    )


def test_performance_keeps_credit_after_soft_delete(tmp_path: Path) -> None:
    bots = tmp_path / "bots.db"
    journal = tmp_path / "journal.db"
    orch = BotOrchestrator(bots)
    a = orch.add_bot("Kraken TIA/USD 4h", "RSI", "TIA/USD", exchange="kraken", timeframe="4h")
    b = orch.add_bot("Kraken BTC/USD 1h", "MACD", "BTC/USD", exchange="kraken", timeframe="1h")
    tj = TradeJournal(journal)
    tj.append_trade(
        TradeRecord("TIA/USD", "long", 100.0, 12.5, "bot", "t", "t1", bot_id=a),
    )
    tj.append_trade(
        TradeRecord("TIA/USD", "long", 100.0, -2.0, "bot", "t", "t2", bot_id=a),
    )
    tj.append_trade(
        TradeRecord("BTC/USD", "long", 100.0, 5.0, "bot", "t", "t3", bot_id=b),
    )
    orch.delete_bot(a)
    assert all(bot["id"] != a for bot in orch.list_bots())
    rows = performance_rows(bots, journal)
    by_id = {r.bot_id: r for r in rows}
    assert a in by_id
    assert by_id[a].retired
    assert by_id[a].trade_count == 2
    assert by_id[a].realized_pnl == 10.5
    assert "(removed)" in by_id[a].display_label
