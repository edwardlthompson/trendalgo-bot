"""Scanner host display-filter persistence."""

from __future__ import annotations

from pathlib import Path

from trendalgo.scanner.host_filters import load_host_filters, save_host_filters


def test_host_filters_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    assert load_host_filters() == {
        "exchanges": [],
        "gain7Text": "",
        "gain30Text": "",
    }
    saved = save_host_filters(
        {
            "exchanges": ["Kraken", "binance", "coinbase"],
            "gain7Text": "10",
            "gain30Text": "30%",
        }
    )
    assert saved == {
        "exchanges": ["kraken", "coinbase"],
        "gain7Text": "10",
        "gain30Text": "30%",
    }
    assert load_host_filters() == saved


def test_config_settings_empty_indicators_means_all(monkeypatch) -> None:
    monkeypatch.delenv("BACKTEST_INDICATORS", raising=False)
    monkeypatch.delenv("BACKTEST_MAX_COINS_PER_RUN", raising=False)
    monkeypatch.setenv("BACKTEST_INDICATORS", "")
    monkeypatch.setenv("BACKTEST_MAX_COINS_PER_RUN", "0")
    import importlib

    from trendalgo.lts_vendor.shims import config_settings

    importlib.reload(config_settings)
    assert config_settings.settings.backtest_indicators == []
    assert config_settings.settings.backtest_max_coins_per_run == 0

    from trendalgo.lts_vendor import install_import_shims

    install_import_shims()
    from trendalgo.lts_vendor.backtesting.params import runner_params_from_settings
    from trendalgo.lts_vendor.backtesting.signals import SIGNAL_REGISTRY

    rp = runner_params_from_settings()
    assert rp.backtest_indicators == ()
    # runner expands empty → full registry
    configured = list(rp.backtest_indicators)
    indicators = (
        [n for n in configured if n in SIGNAL_REGISTRY]
        if configured
        else list(SIGNAL_REGISTRY.keys())
    )
    assert "RSI" in indicators
    assert "MACD" in indicators
    assert "Heikin Ashi" in indicators
    assert len(indicators) == len(SIGNAL_REGISTRY)
