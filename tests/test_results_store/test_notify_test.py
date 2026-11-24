"""Notify delivery test helpers — vault gate without live send."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.notify_test import send_telegram_test


def test_telegram_missing_creds(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "trendalgo.results_store.notify_test.load_telegram_creds",
        lambda: (None, None),
    )
    result = send_telegram_test(tmp_path)
    assert result["ok"] is False
    assert result["error"] == "missing_creds"
