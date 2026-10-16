"""Top-level import shims for vendored LTS backtesting (api.*, database.*, …)."""

from __future__ import annotations

import sys
import types


def install() -> None:
    from trendalgo.lts_vendor.shims import (
        api_coingecko,
        api_price_history_fallback,
        config_settings,
        database_cache,
        provider_circuit,
        provider_rate_limit,
    )

    def _pkg(name: str) -> types.ModuleType:
        mod = sys.modules.get(name)
        if mod is None:
            mod = types.ModuleType(name)
            sys.modules[name] = mod
        return mod

    api = _pkg("api")
    api.coingecko = api_coingecko  # type: ignore[attr-defined]
    api.price_history_fallback = api_price_history_fallback  # type: ignore[attr-defined]
    sys.modules["api.coingecko"] = api_coingecko
    sys.modules["api.price_history_fallback"] = api_price_history_fallback

    database = _pkg("database")
    database.cache = database_cache  # type: ignore[attr-defined]
    sys.modules["database.cache"] = database_cache

    utils = _pkg("utils")
    utils.provider_circuit = provider_circuit  # type: ignore[attr-defined]
    utils.provider_rate_limit = provider_rate_limit  # type: ignore[attr-defined]
    sys.modules["utils.provider_circuit"] = provider_circuit
    sys.modules["utils.provider_rate_limit"] = provider_rate_limit

    config = _pkg("config")
    config.settings = config_settings  # type: ignore[attr-defined]
    sys.modules["config.settings"] = config_settings
