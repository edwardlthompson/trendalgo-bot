"""Unit tests for qualified/watchlist alert diffs and prefs gating."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.alert_dispatch import plans_for, trade_telegram_enabled
from trendalgo.device.notify_prefs import NotifyPrefs, load_prefs, save_prefs
from trendalgo.device.scanner_alert_diff import coin_keys, diff_alerts
from trendalgo.device.scanner_alerts_store import (
    append_alerts,
    load_history,
    load_previous_qualified,
    save_previous_qualified,
)
from trendalgo.device.scanner_schedule import clamp_interval_minutes
from trendalgo.device.telegram_vault import (
    load_telegram_creds,
    memory_store_for_tests,
    save_telegram_creds,
)
from trendalgo.notifications.telegram_format import format_qualified_enter, format_trade


def test_diff_enter_and_filtered_leave() -> None:
    previous = {"AAA", "BBB"}
    current = [{"symbol": "BBB"}, {"symbol": "CCC", "pair": "CCC/USD"}]
    events = diff_alerts(previous=previous, current_coins=current, watchlist=set())
    kinds = {(e.kind, e.symbol) for e in events}
    assert ("qualified_enter", "CCC") in kinds
    assert ("watchlist_leave", "AAA") in kinds  # left filtered set (no watchlist required)
    assert ("watchlist_leave", "BBB") not in kinds  # still in filtered set


def test_filtered_leave_uses_board_metrics_for_reason() -> None:
    previous = {"KEEP", "DROP"}
    current = [{"symbol": "KEEP", "pair": "KEEP/USD", "bot_best_net_pct": 50.0}]
    board = [
        {"symbol": "KEEP", "pair": "KEEP/USD", "bot_best_net_pct": 50.0},
        {"symbol": "DROP", "pair": "DROP/USD", "bot_best_net_pct": 12.0},
    ]
    events = diff_alerts(
        previous=previous,
        current_coins=current,
        watchlist=set(),
        board_coins=board,
        floors={"min_best_bt": 30.0},
    )
    leave = next(e for e in events if e.kind == "watchlist_leave" and e.symbol == "DROP")
    assert "Best BT 12.0% below min 30.0%" in leave.reason
    assert leave.coin is not None
    assert leave.coin.get("bot_best_net_pct") == 12.0


def test_leave_reason_uses_floors_and_snapshot() -> None:
    from trendalgo.device.scanner_alert_diff import leave_reason

    reason = leave_reason(
        "AAA",
        {"volume_24h": 12_000, "uniformity_score": 0.41, "pair": "AAA/USD"},
        floors={"min_volume_usd": 50_000, "min_uniformity": 0.55},
    )
    assert "Volume $12,000 below min $50,000" in reason
    assert "Uniformity 0.41 < 0.55" in reason
    assert "scan floors" not in reason.lower()


def test_leave_reason_cites_best_bt_and_gains() -> None:
    from trendalgo.device.scanner_alert_diff import leave_reason

    reason = leave_reason(
        "AKE",
        {
            "bot_best_net_pct": 12.0,
            "gain_7d": 5.0,
            "pair": "AKE/USD",
        },
        floors={"min_best_bt": 30.0, "min_gain_7d": 10.0},
    )
    assert "Best BT 12.0% below min 30.0%" in reason
    assert "7D gain 5.0% below min 10.0%" in reason


def test_previous_coins_roundtrip(tmp_path: Path) -> None:
    from trendalgo.device.scanner_alerts_store import load_previous_coins

    save_previous_qualified(
        tmp_path,
        {"ETH"},
        coins=[{"symbol": "ETH", "pair": "ETH/USD", "volume_24h": 99_000}],
    )
    coins = load_previous_coins(tmp_path)
    assert coins["ETH"]["volume_24h"] == 99_000
    events = diff_alerts(
        previous={"ETH"},
        current_coins=[],
        watchlist={"ETH"},
        previous_coins=coins,
        floors={"min_volume_usd": 200_000},
    )
    assert events[0].kind == "watchlist_leave"
    assert "Volume" in events[0].reason


def test_alert_store_roundtrip(tmp_path: Path) -> None:
    save_previous_qualified(tmp_path, {"ETH", "BTC"})
    assert load_previous_qualified(tmp_path) == {"BTC", "ETH"}
    events = diff_alerts(
        previous=set(),
        current_coins=[{"symbol": "ETH"}],
        watchlist=set(),
    )
    history = append_alerts(tmp_path, events)
    assert len(history) == 1
    assert load_history(tmp_path)[0]["symbol"] == "ETH"


def test_prefs_gate_channels(tmp_path: Path) -> None:
    prefs = NotifyPrefs(
        windows_entered=False,
        windows_left=True,
        telegram_enabled=True,
        telegram_entered=False,
        telegram_left=True,
    )
    save_prefs(tmp_path, prefs)
    loaded = load_prefs(tmp_path)
    events = diff_alerts(
        previous={"AAA"},
        current_coins=[{"symbol": "BBB"}],
        watchlist={"AAA"},
    )
    plans = plans_for(events, loaded)
    assert all(p.events[0].kind == "watchlist_leave" for p in plans)
    assert trade_telegram_enabled(
        NotifyPrefs(windows_trades=True, telegram_enabled=True, telegram_trades=True)
    )


def test_clamp_interval() -> None:
    assert clamp_interval_minutes(5) == 60
    assert clamp_interval_minutes(2000) == 1440
    assert clamp_interval_minutes(90) == 90


def test_telegram_vault_memory() -> None:
    store = memory_store_for_tests()
    save_telegram_creds("tok", "123", store=store)
    token, chat = load_telegram_creds(store)
    assert token == "tok"
    assert chat == "123"


def test_formatters_smoke() -> None:
    text = format_qualified_enter(
        {
            "symbol": "ETH",
            "pair": "ETH/USD",
            "gain_7d": 12.5,
            "gain_30d": 40,
            "health": 0.9,
            "uniformity": 0.8,
        }
    )
    assert "ETH" in text
    trade = format_trade(
        pair="BTC/USD",
        side="buy",
        amount=0.01,
        price=100.0,
        plan_version=3,
    )
    assert "BTC/USD" in trade
    assert coin_keys([{"symbol": "x"}]) == {"X"}


def test_process_scan_alerts_cold_seed_then_enter(tmp_path: Path) -> None:
    from trendalgo.device.scan_alerts import process_scan_alerts
    from trendalgo.notifications.telegram import TelegramCommands

    class _Silent(TelegramCommands):
        def __init__(self) -> None:
            super().__init__(token="t", chat_id="1")
            self.messages: list[str] = []

        def send_message(self, text: str, **_kw: object) -> bool:
            self.messages.append(text)
            return True

        def send_photo(self, png: bytes, caption: str = "", **_kw: object) -> bool:
            self.messages.append(caption)
            return True

    save_prefs(
        tmp_path,
        NotifyPrefs(
            windows_entered=True,
            windows_left=True,
            telegram_enabled=True,
            telegram_entered=True,
        ),
    )
    tg = _Silent()
    first, _hist = process_scan_alerts(
        tmp_path,
        coins=[
            {"symbol": "SOL", "pair": "SOL/USD", "bot_best_net_pct": 40.0},
            {"symbol": "ETH", "pair": "ETH/USD", "bot_best_net_pct": 55.0},
        ],
        watchlist_pairs=[],
        telegram=tg,
    )
    assert first == []
    assert load_previous_qualified(tmp_path) == {"ETH", "SOL"}
    assert tg.messages == []

    second, history = process_scan_alerts(
        tmp_path,
        coins=[
            {"symbol": "SOL", "pair": "SOL/USD", "bot_best_net_pct": 40.0},
            {"symbol": "ETH", "pair": "ETH/USD", "bot_best_net_pct": 55.0},
            {"symbol": "BTC", "pair": "BTC/USD", "bot_best_net_pct": 80.0},
        ],
        watchlist_pairs=[],
        telegram=tg,
    )
    assert [(e.kind, e.symbol) for e in second] == [("qualified_enter", "BTC")]
    assert history
    assert load_previous_qualified(tmp_path) == {"BTC", "ETH", "SOL"}


def test_filtered_caller_drops_below_best_bt() -> None:
    """Caller pre-filters like Qualified tab; weak coins never enter the diff set."""
    from trendalgo.device.lts_scan_model import filter_coins

    board = [
        {"symbol": "WEAK", "pair": "WEAK/USD", "bot_best_net_pct": 10.0, "gains": {"7d": 40}},
        {"symbol": "STRONG", "pair": "STRONG/USD", "bot_best_net_pct": 50.0, "gains": {"7d": 40}},
    ]
    alertable = filter_coins(board, min_best_bt=30.0, min_gain_7d=20.0)
    assert [c["symbol"] for c in alertable] == ["STRONG"]
    events = diff_alerts(
        previous=set(),
        current_coins=alertable,
        watchlist=set(),
    )
    assert [(e.kind, e.symbol) for e in events] == [("qualified_enter", "STRONG")]
