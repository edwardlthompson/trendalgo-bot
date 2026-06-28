"""Glossary cross-link metadata."""

from trendalgo.ta.glossary import glossary_entry


def test_abandoned_baby_links_to_doji() -> None:
    entry = glossary_entry("CDLABANDONEDBABY")
    assert "[[CDLDOJI|doji]]" in entry["short"]
    assert "CDLDOJI" in entry.get("related", [])


def test_doji_is_link_target() -> None:
    entry = glossary_entry("CDLDOJI")
    assert entry["title"] == "Doji"
