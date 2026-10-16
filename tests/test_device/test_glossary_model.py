"""Pure tests for bundled TA glossary load and filter."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.glossary_model import (
    bundled_glossary_path,
    filter_entries,
    find_glossary_entry,
    load_glossary,
    normalize_glossary_query,
)


def test_bundled_glossary_loads_many_entries() -> None:
    entries, error = load_glossary()
    assert error is None
    assert len(entries) >= 300
    assert bundled_glossary_path().is_file()


def test_filter_matches_title_and_id() -> None:
    entries, _ = load_glossary()
    adx = filter_entries(entries, "ADX")
    assert any(entry.id == "ADX" for entry in adx)
    rsi = filter_entries(entries, "relative strength")
    assert any("RSI" in entry.id for entry in rsi)


def test_load_glossary_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    entries, error = load_glossary(path)
    assert entries == []
    assert error is not None


def test_load_glossary_requires_entries(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"entries": []}), encoding="utf-8")
    entries, error = load_glossary(path)
    assert entries == []
    assert error is not None


def test_find_glossary_entry_by_id_and_star_suffix() -> None:
    entries, error = load_glossary()
    assert error is None
    assert normalize_glossary_query("RSI *") == "RSI"
    rsi = find_glossary_entry(entries, "RSI *")
    assert rsi is not None
    assert rsi.id == "RSI"
    assert find_glossary_entry(entries, "no-such-ta-xyz") is None
