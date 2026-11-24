"""AV-G-RES5 — glossary entry payload keys for Avalonia popup."""

from __future__ import annotations

from trendalgo.results_store.desk_more import load_glossary_surface


def test_glossary_entry_keys_for_shell() -> None:
    data = load_glossary_surface(query="MACD")
    assert "entry" in data
    assert "found" in data
    assert "miss_title" in data
    assert "miss_body" in data
    if data["found"]:
        entry = data["entry"]
        for key in ("title", "subtitle", "long", "formula", "formula_label", "pool", "category"):
            assert key in entry
