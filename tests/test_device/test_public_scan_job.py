"""Public Kraken scan path when vault has no keyed venues."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from trendalgo.device.scan_job import scan_job
from trendalgo.device.scan_model import ScanUnavailableError
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot


def _snap(*, degraded: bool = False) -> QualifiedSnapshot:
    now = datetime.now(tz=UTC)
    return QualifiedSnapshot(
        generated_at=now,
        as_of=now,
        scan_id=1,
        degraded=degraded,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.9,
                gain_pct=1.0,
                volume_score=1.0,
                entry_signal=True,
            )
        ],
    )


def test_scan_job_public_when_no_venues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "trendalgo.device.scan_job.resolve_scan_exchange_ids",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr("trendalgo.device.scan_job.VaultSecretStore", lambda *a, **k: MagicMock())
    monkeypatch.setattr("trendalgo.device.scan_job.set_secret_store", lambda *_a, **_k: None)
    monkeypatch.setattr("trendalgo.device.scan_job.load_filters", lambda *_a, **_k: {})
    monkeypatch.setattr(
        "trendalgo.device.scan_job.device_scan_settings", lambda *_a, **_k: object()
    )
    monkeypatch.setattr("trendalgo.device.scan_job.run_pipeline", lambda *_a, **_k: _snap())
    monkeypatch.setattr(
        "trendalgo.device.scan_job.build_lts_rows",
        lambda snap, **_k: [{"symbol": "BTC", "pair": "BTC/USD", "exchange_id": "kraken"}],
    )
    monkeypatch.setattr("trendalgo.device.scan_job._save", lambda *_a, **_k: 7)
    monkeypatch.setattr("trendalgo.device.scan_job.save_lts_rows", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "trendalgo.device.scan_job._merge_pass1_backtests",
        lambda rows, root: (rows, {}),
    )
    monkeypatch.setattr(
        "trendalgo.device.lts_scan_model.coins_for_backtest",
        lambda rows, _saved: rows,
    )

    result = scan_job(tmp_path)
    assert result["scan_mode"] == "public"
    assert result["data_source"] == "Kraken public"
    assert result["venues"] == ["kraken"]
    assert result["rows"] >= 1


def test_scan_job_public_raises_on_pipeline_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "trendalgo.device.scan_job.resolve_scan_exchange_ids",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr("trendalgo.device.scan_job.VaultSecretStore", lambda *a, **k: MagicMock())
    monkeypatch.setattr("trendalgo.device.scan_job.set_secret_store", lambda *_a, **_k: None)
    monkeypatch.setattr("trendalgo.device.scan_job.load_filters", lambda *_a, **_k: {})
    monkeypatch.setattr(
        "trendalgo.device.scan_job.device_scan_settings", lambda *_a, **_k: object()
    )
    monkeypatch.setattr(
        "trendalgo.device.scan_job.run_pipeline",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("down")),
    )
    with pytest.raises(ScanUnavailableError):
        scan_job(tmp_path)


def test_scanner_source_badge_strings() -> None:
    from trendalgo.device import strings as S

    assert "Kraken public" in S.SCANNER_SOURCE_PUBLIC
    assert "{venues}" in S.SCANNER_SOURCE_KEYED
    assert S.SCAN_REFRESH_PRICES
    assert S.BACKTEST_REFRESH_PRICES
