"""Human-readable TA strategy glossary for tooltips and novice docs."""

from __future__ import annotations

from typing import Any

from trendalgo.ta.catalog import all_ta_names
from trendalgo.ta.categories import ta_category
from trendalgo.ta.extended_glossary_data import EXTENDED_GLOSSARY_ENTRIES
from trendalgo.ta.glossary_crosslinks import GLOSSARY_RELATED
from trendalgo.ta.glossary_data import GLOSSARY_ENTRIES
from trendalgo.ta.pandas_ta_glossary_data import PANDAS_TA_GLOSSARY_ENTRIES


def _merged_entries() -> dict[str, dict[str, str]]:
    return {**GLOSSARY_ENTRIES, **EXTENDED_GLOSSARY_ENTRIES, **PANDAS_TA_GLOSSARY_ENTRIES}


def _entry_fields(fn_id: str) -> dict[str, str]:
    merged = _merged_entries()
    if fn_id not in merged:
        raise KeyError(f"Unknown TA function: {fn_id}")
    return merged[fn_id]


def glossary_entry(fn_id: str) -> dict[str, Any]:
    key = fn_id.upper()
    payload: dict[str, Any] = {"id": key, "category": ta_category(key), **_entry_fields(key)}
    related = GLOSSARY_RELATED.get(key)
    if related:
        payload["related"] = related
    return payload


def build_ta_glossary() -> list[dict[str, Any]]:
    return [glossary_entry(fn_id) for fn_id in sorted(set(all_ta_names()))]


def glossary_lookup() -> dict[str, dict[str, Any]]:
    return {fn_id: glossary_entry(fn_id) for fn_id in all_ta_names()}


def glossary_payload() -> dict[str, Any]:
    entries = build_ta_glossary()
    return {"entries": entries, "count": len(entries)}
