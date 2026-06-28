"""Glossary coverage tests for TA function metadata."""

from trendalgo.ta.catalog import TA_FUNCTION_NAMES, all_ta_count
from trendalgo.ta.glossary import build_ta_glossary
from trendalgo.ta.glossary_data import GLOSSARY_ENTRIES


def test_glossary_has_full_ta_coverage() -> None:
    assert len(build_ta_glossary()) == all_ta_count()
    assert len(GLOSSARY_ENTRIES) == len(TA_FUNCTION_NAMES)


def test_each_ta_function_has_non_empty_fields() -> None:
    placeholders = 0
    for entry in build_ta_glossary():
        assert entry["title"].strip()
        assert entry["short"].strip()
        assert entry["long"].strip()
        assert entry.get("category", "").strip()
        formula = entry["formula"].strip()
        assert formula
        assert "documentation" not in formula.lower()
        assert "pandas-ta-classic `" not in formula.lower()
        if formula.startswith("Default inputs:") and len(formula) < 40:
            placeholders += 1
    assert placeholders < 20
