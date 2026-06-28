"""Icon registry tests."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.icons.store import IconStore
from trendalgo.icons.sync import sync_exchanges


def test_sync_exchanges_writes_db(tmp_path: Path, monkeypatch) -> None:
    web_registry = tmp_path / "web" / "icon-registry"
    icon_dir = tmp_path / "icons" / "exchanges"
    config = tmp_path / "exchange-icons.json"
    config.write_text(
        json.dumps(
            {
                "version": 2,
                "exchanges": {
                    "kraken": {
                        "brand": "Kraken",
                        "color": "#5741D9",
                        "source_url": "https://example.com/kraken.png",
                        "icon": "/icons/exchanges/kraken.png",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("trendalgo.icons.sync._WEB_REGISTRY", web_registry)
    monkeypatch.setattr("trendalgo.icons.sync._EXCHANGE_ICON_DIR", icon_dir)
    monkeypatch.setattr("trendalgo.icons.sync._EXCHANGE_CONFIG", config)
    monkeypatch.setattr(
        "trendalgo.icons.sync._download_file",
        lambda _url, dest: dest.write_bytes(b"fake-png"),
    )
    store = IconStore(tmp_path / "icon-registry.db")
    result = sync_exchanges(store, refresh=True)
    assert result["exchange_count"] == 1
    row = store.get_exchange("kraken")
    assert row is not None
    assert row["icon_path"] == "/icons/exchanges/kraken.png"
    assert (icon_dir / "kraken.png").is_file()
    assert (web_registry / "exchanges.json").is_file()
