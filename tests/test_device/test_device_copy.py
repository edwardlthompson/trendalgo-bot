"""Copy guard: no device text points at the retired main app or PWA, and the honest notes stay."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device import strings as S
from trendalgo.device.backtest_model import missing_candles_text

DEVICE_SRC = Path(__file__).resolve().parents[2] / "src" / "trendalgo" / "device"
RETIRED_WORDS = ("main app", "PWA")


def test_no_device_source_mentions_the_retired_main_app_or_pwa() -> None:
    offenders = []
    for path in sorted(DEVICE_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        offenders.extend(f"{path.name}: {word}" for word in RETIRED_WORDS if word in text)
    assert offenders == []


def test_the_scanner_copy_names_the_run_button_and_keyed_venues() -> None:
    assert "API keys" in S.SCANNER_SUBTITLE
    assert S.SCANNER_TITLE == "Opportunity scanner"
    assert "Run scan" in S.SCANNER_EMPTY_BODY
    assert "Run scan" in S.SCANNER_NONE_BODY
    assert "Qualified" in S.SCANNER_TAB_QUALIFIED
    assert "API calls this minute" in S.SETTINGS_KEYS_RATE


def test_the_settings_note_names_where_the_secret_lives_without_jargon() -> None:
    assert "Credential Manager" in S.SETTINGS_NO_SECRET
    assert "sign" not in S.SETTINGS_NO_SECRET


def test_missing_candles_names_the_data_folder_and_says_no_download() -> None:
    text = missing_candles_text("BTC/USD", "1h")
    assert "data folder" in text
    assert "does not download them" in text
