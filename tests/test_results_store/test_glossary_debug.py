"""Glossary search + debug log surfaces (gap depth)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.desk_more import load_debug_surface, load_glossary_surface


def test_glossary_surface_filters() -> None:
    data = load_glossary_surface(query="rsi")
    assert data["total"] > 0
    assert data["shown"] >= 1
    assert any("RSI" in r["id"].upper() or "RSI" in r["title"].upper() for r in data["rows"])


def test_glossary_surface_full_entry() -> None:
    data = load_glossary_surface(query="RSI")
    assert data["found"] is True
    entry = data["entry"]
    assert entry is not None
    assert "RSI" in entry["title"].upper() or entry["id"].upper() == "RSI"
    assert entry["long"]
    assert entry["formula"]
    assert entry["formula_label"]
    assert "·" in entry["subtitle"]


def test_glossary_surface_miss() -> None:
    data = load_glossary_surface(query="zzznomatch-xyz")
    assert data["found"] is False
    assert data["entry"] is None
    assert data["miss_title"]
    assert "zzznomatch" in data["miss_body"]


def test_debug_surface_tails_log(tmp_path: Path) -> None:
    (tmp_path / "device.log").write_text("a\nb\nc\n", encoding="utf-8")
    data = load_debug_surface(tmp_path)
    assert data["exists"] is True
    assert data["lines"] == ["a", "b", "c"]
