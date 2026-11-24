"""AV-G-STR5 — Shell autostart shares PySide Run value name."""

from __future__ import annotations

from trendalgo.device.autostart import RUN_KEY, VALUE_NAME


def test_autostart_registry_constants() -> None:
    assert VALUE_NAME == "TrendAlgoBot"
    assert RUN_KEY.endswith(r"\Run")
