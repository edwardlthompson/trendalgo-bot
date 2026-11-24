"""Tests for POL3-01 (Losses/Strength derivation) and POL3-03 (rich per-lane Telegram alerts)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.desk_scan_alerts import emit_desk_scan_alerts
from trendalgo.device.lts_scan_model import save_lts_rows
from trendalgo.device.notify_prefs import NotifyPrefs, save_prefs
from trendalgo.device.scanner_alerts_store import load_previous_qualified
from trendalgo.results_store.desk_surfaces import strategy_sheet_from_coin


class _FakeTelegram:
    def __init__(self) -> None:
        self.enabled = True
        self.photos: list[tuple[bytes, str, str | None]] = []
        self.messages: list[tuple[str, str | None]] = []

    def send_photo(
        self,
        png: bytes,
        caption: str = "",
        *,
        parse_mode: str | None = None,
        reply_markup: str | dict[str, Any] | None = None,
    ) -> bool:
        del parse_mode
        self.photos.append((png, caption, reply_markup if isinstance(reply_markup, str) else None))
        return True

    def send_message(
        self,
        text: str,
        *,
        parse_mode: str | None = None,
        reply_markup: str | dict[str, Any] | None = None,
    ) -> bool:
        del parse_mode
        self.messages.append((text, reply_markup if isinstance(reply_markup, str) else None))
        return True


def test_strategy_sheet_populates_losses_and_strength() -> None:
    coin = {
        "pair": "BTC/USD",
        "backtest_top_strategies": [
            {
                "indicator": "RSI",
                "timeframe": "1h",
                "net_pct": 42.5,
                "trades": 12,
                "open_trades": 1,
                "wins": 9,
                "tsl_hits": 1,
                "trailing_stop_loss_pct": 5.0,
            }
        ],
        "backtest_buy_hold": {"indicator": "B&H", "timeframe": "1h", "net_pct": 12.0},
    }
    rows = strategy_sheet_from_coin(coin)
    rsi = next(r for r in rows if r.get("indicator") == "RSI")
    assert rsi["losses"] == 2
    assert isinstance(rsi["strength"], float) and rsi["strength"] > 0


def test_emit_desk_scan_alerts_per_lane_and_rich_telegram(tmp_path: Path) -> None:
    save_prefs(
        tmp_path,
        NotifyPrefs(
            telegram_enabled=True,
            telegram_entered=True,
            telegram_left=True,
            windows_entered=True,
            windows_left=True,
        ),
    )
    ohlc = [[100.0 + i, 102.0 + i, 99.0 + i, 101.0 + i] for i in range(24)]
    btc = {
        "symbol": "BTC",
        "name": "Bitcoin",
        "pair": "BTC/USD",
        "gain_7d": 12.5,
        "gain_30d": 28.0,
        "volume_24h": 5_000_000.0,
        "health_score": 82,
        "ohlc_1h": ohlc,
        "backtest_top_strategies": [
            {
                "indicator": "RSI",
                "timeframe": "1h",
                "net_pct": 35.0,
                "trades": 10,
                "wins": 8,
                "tsl_hits": 0,
            }
        ],
    }
    eth = {
        "symbol": "ETH",
        "name": "Ethereum",
        "pair": "ETH/USD",
        "gain_7d": 9.0,
        "gain_30d": 18.0,
        "volume_24h": 3_000_000.0,
        "health_score": 78,
        "ohlc_1h": ohlc,
        "backtest_top_strategies": [
            {
                "indicator": "EMA",
                "timeframe": "1h",
                "net_pct": 25.0,
                "trades": 8,
                "wins": 7,
                "tsl_hits": 0,
            }
        ],
    }
    aapl = {"symbol": "AAPL", "name": "Apple", "pair": "AAPL/USD", "gain_7d": 6.0, "gain_30d": 11.0}

    tg = _FakeTelegram()
    # Cold seed crypto with BTC; tradfi with AAPL (separate state file)
    save_lts_rows(tmp_path, [btc], lane="crypto")
    assert emit_desk_scan_alerts(tmp_path, lane="crypto", telegram=tg) == []  # type: ignore[arg-type]
    save_lts_rows(tmp_path, [aapl], lane="tradfi")
    assert emit_desk_scan_alerts(tmp_path, lane="tradfi", telegram=tg) == []  # type: ignore[arg-type]
    assert load_previous_qualified(tmp_path, lane="crypto") == {"BTC"}
    assert load_previous_qualified(tmp_path, lane="tradfi") == {"AAPL"}

    # Second crypto scan adds ETH -> rich photo alert with HTML caption + inline keyboard
    save_lts_rows(tmp_path, [btc, eth], lane="crypto")
    events = emit_desk_scan_alerts(tmp_path, lane="crypto", telegram=tg)  # type: ignore[arg-type]
    assert [e.kind for e in events] == ["qualified_enter"]
    if tg.photos:
        assert len(tg.photos) == 1
        png, caption, markup = tg.photos[0]
        assert png.startswith(b"\x89PNG")
    else:
        assert len(tg.messages) == 1
        caption, markup = tg.messages[0]
    assert "ETH" in caption
    assert markup and "inline_keyboard" in markup
