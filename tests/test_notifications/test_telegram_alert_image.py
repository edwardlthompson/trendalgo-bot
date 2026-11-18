"""Composite Telegram alert PNG smoke."""

from __future__ import annotations

from trendalgo.device.alert_preview import sample_event
from trendalgo.notifications.telegram_alert_image import build_enter_alert_png, build_exit_alert_png
from trendalgo.notifications.telegram_chart import closes_from_coin


def test_closes_from_coin_reads_spark() -> None:
    assert closes_from_coin({"spark_closes_7d": [1, 2, 3]}) == [1.0, 2.0, 3.0]


def test_enter_alert_png_from_sample() -> None:
    coin = sample_event("entered").coin
    assert coin is not None
    png = build_enter_alert_png(coin)
    if png is not None:
        assert png[:4] == b"\x89PNG"


def test_exit_alert_png_from_sample() -> None:
    coin = sample_event("left").coin
    assert coin is not None
    png = build_exit_alert_png(coin)
    if png is not None:
        assert png[:4] == b"\x89PNG"
