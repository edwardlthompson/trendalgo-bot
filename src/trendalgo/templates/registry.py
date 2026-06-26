"""Strategy template registry (ADR-0001 plugin pattern, native runtime)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyTemplate:
    """Metadata for a registered native strategy module."""

    id: str
    module_path: str
    description: str
    timeframes: tuple[str, ...]
    kind: str = "custom"


_REGISTRY: dict[str, StrategyTemplate] = {}


def register(template: StrategyTemplate) -> StrategyTemplate:
    _REGISTRY[template.id] = template
    return template


def get(template_id: str) -> StrategyTemplate | None:
    return _REGISTRY.get(template_id)


def list_templates() -> list[StrategyTemplate]:
    return sorted(_REGISTRY.values(), key=lambda t: t.id)


def clear_registry() -> None:
    """Test helper."""
    _REGISTRY.clear()


_RUNTIME = "src/trendalgo/strategies/runtime"

register(
    StrategyTemplate(
        id="multi-tf-example",
        module_path=f"{_RUNTIME}/multi_tf.py",
        description="Multi-timeframe RSI + EMA example on Kraken spot",
        timeframes=("5m", "1h"),
        kind="multi-tf",
    )
)
register(
    StrategyTemplate(
        id="strong-uptrend-scanner",
        module_path=f"{_RUNTIME}/multi_tf.py",
        description="Strong Uptrend Scanner — LTS uniformity gate + TrendSpotter Boost",
        timeframes=("5m", "1h"),
        kind="scanner",
    )
)
register(
    StrategyTemplate(
        id="smart-dca",
        module_path=f"{_RUNTIME}/smart_dca.py",
        description="Smart DCA — interval buys with dip acceleration (T9)",
        timeframes=("1h",),
        kind="dca",
    )
)
register(
    StrategyTemplate(
        id="grid-trading",
        module_path=f"{_RUNTIME}/grid_trading.py",
        description="Grid trading — spaced limit-style entries on Kraken spot (T11)",
        timeframes=("5m",),
        kind="grid",
    )
)
register(
    StrategyTemplate(
        id="multi-tf-ta",
        module_path=f"{_RUNTIME}/multi_tf.py",
        description="Multi-TF TA preset — faster RSI + dual EMA (importable)",
        timeframes=("5m", "1h"),
        kind="multi-tf",
    )
)
