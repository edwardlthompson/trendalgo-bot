"""Icon registry tests."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.icons.aliases import resolve_symbol
from trendalgo.icons.store import IconStore
from trendalgo.icons.sync import sync_coin_extras, sync_exchanges


def test_lighter_alias_maps_to_lit() -> None:
    assert resolve_symbol("LIGHTER") == "LIT"


def test_sync_coin_extras_writes_curated(tmp_path: Path, monkeypatch) -> None:
    extras = tmp_path / "coin-icon-extras.json"
    curated = tmp_path / "coins"
    extras.write_text(
        json.dumps(
            {
                "coins": {
                    "AKE": {"coingecko_id": "akedo", "name": "Akedo"},
                    "LIGHTER": {"coingecko_id": "lighter", "name": "Lighter"},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("trendalgo.icons.sync._COIN_EXTRAS", extras)
    monkeypatch.setattr("trendalgo.icons.sync._CURATED_COIN_DIR", curated)
    monkeypatch.setattr(
        "trendalgo.icons.sync._fetch_json",
        lambda _url: {
            "name": "Akedo",
            "market_cap_rank": 100,
            "image": {"large": "https://example.com/ake.png"},
        },
    )
    monkeypatch.setattr(
        "trendalgo.icons.sync._download_file",
        lambda _url, dest: dest.write_bytes(b"fake-png"),
    )
    store = IconStore(tmp_path / "icon-registry.db")
    result = sync_coin_extras(store, refresh=True)
    assert result["extra_count"] == 2
    assert (curated / "AKE.png").is_file()
    assert (curated / "LIGHTER.png").is_file()


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
