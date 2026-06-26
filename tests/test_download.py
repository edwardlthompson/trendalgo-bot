from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from trendalgo.data.download import download_ohlcv, main, save_csv


def test_save_csv(tmp_path: Path) -> None:
    rows = [[1, 1.0, 2.0, 0.5, 1.5, 10.0]]
    out = tmp_path / "btc.csv"
    save_csv(rows, out)
    text = out.read_text(encoding="utf-8")
    assert "timestamp,open" in text
    assert "1,1.0" in text


@patch("trendalgo.data.download._exchange")
def test_download_ohlcv(mock_ex: MagicMock) -> None:
    exchange = MagicMock()
    exchange.fetch_ohlcv.return_value = [[1, 1, 2, 0.5, 1.5, 9]]
    mock_ex.return_value = exchange
    rows = download_ohlcv("BTC/USD", "5m", 1)
    assert len(rows) == 1
    exchange.fetch_ohlcv.assert_called_once()


@patch("trendalgo.data.download.download_ohlcv", return_value=[[1, 1, 2, 0.5, 1.5, 9]])
def test_main_ok(mock_dl: MagicMock, tmp_path: Path) -> None:
    code = main(["--out", str(tmp_path), "--pair", "BTC/USD"])
    assert code == 0
    assert list(tmp_path.glob("*.csv"))
