"""Load and filter bundled TA glossary entries for the device Glossary page."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REL = Path("trendalgo") / "device" / "data" / "ta-glossary.json"
_SOURCE = Path(__file__).resolve().parent / "data" / "ta-glossary.json"


@dataclass(frozen=True)
class GlossaryEntry:
    id: str
    category: str
    title: str
    short: str
    long: str
    formula: str
    related: tuple[str, ...] = ()


_CACHE: tuple[list[GlossaryEntry], str | None] | None = None


def bundled_glossary_path() -> Path:
    """Dev checkout path, or the PyInstaller data copy under ``_MEIPASS``."""
    for candidate in _glossary_candidates():
        if candidate.is_file():
            return candidate
    return _glossary_candidates()[0]


def _glossary_candidates() -> list[Path]:
    out: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if isinstance(meipass, str):
        root = Path(meipass)
        out.append(root / _REL)
        out.append(root / "device" / "data" / "ta-glossary.json")
    out.append(_SOURCE)
    return out


def clear_glossary_cache() -> None:
    """Test helper: drop the in-memory glossary cache."""
    global _CACHE
    _CACHE = None


def _parse_entry(raw: Any) -> GlossaryEntry | None:
    if not isinstance(raw, dict):
        return None
    entry_id = str(raw.get("id", "")).strip()
    title = str(raw.get("title", "")).strip()
    short = str(raw.get("short", "")).strip()
    long_text = str(raw.get("long", "")).strip()
    formula = str(raw.get("formula", "")).strip()
    category = str(raw.get("category", "")).strip()
    if not entry_id or not title or not short or not long_text or not formula:
        return None
    related_raw = raw.get("related")
    related: tuple[str, ...] = ()
    if isinstance(related_raw, list):
        related = tuple(str(item).strip() for item in related_raw if str(item).strip())
    return GlossaryEntry(
        id=entry_id,
        category=category or "Uncategorized",
        title=title,
        short=short,
        long=long_text,
        formula=formula,
        related=related,
    )


def load_glossary(path: Path | None = None) -> tuple[list[GlossaryEntry], str | None]:
    """Read glossary JSON. Returns (entries, error). Entries are sorted by title then id."""
    global _CACHE
    if path is None and _CACHE is not None:
        return _CACHE
    target = path if path is not None else bundled_glossary_path()
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except OSError as exc:
        result: tuple[list[GlossaryEntry], str | None] = (
            [],
            f"Could not read glossary file: {exc.strerror or exc}",
        )
        if path is None:
            _CACHE = result
        return result
    except json.JSONDecodeError:
        result = ([], "Glossary file is not valid JSON.")
        if path is None:
            _CACHE = result
        return result
    if not isinstance(document, dict):
        result = ([], "Glossary file has an unexpected shape.")
        if path is None:
            _CACHE = result
        return result
    rows = document.get("entries")
    if not isinstance(rows, list) or not rows:
        result = ([], "Glossary file has no entries.")
        if path is None:
            _CACHE = result
        return result
    parsed: list[GlossaryEntry] = []
    for row in rows:
        entry = _parse_entry(row)
        if entry is not None:
            parsed.append(entry)
    if not parsed:
        result = ([], "Glossary file has no usable entries.")
        if path is None:
            _CACHE = result
        return result
    parsed.sort(key=lambda item: (item.title.casefold(), item.id.casefold()))
    result = (parsed, None)
    if path is None:
        _CACHE = result
    return result


def filter_entries(entries: list[GlossaryEntry], query: str) -> list[GlossaryEntry]:
    needle = query.strip().casefold()
    if not needle:
        return list(entries)
    out: list[GlossaryEntry] = []
    for entry in entries:
        haystack = " ".join(
            (
                entry.id,
                entry.category,
                entry.title,
                entry.short,
                entry.long,
                entry.formula,
                " ".join(entry.related),
            )
        ).casefold()
        if needle in haystack:
            out.append(entry)
    return out


def normalize_glossary_query(raw: str) -> str:
    """Strip Results display suffixes (e.g. ' *') for lookup."""
    text = str(raw or "").strip()
    if text.endswith(" *"):
        text = text[:-2].strip()
    return text


def find_glossary_entry(
    entries: list[GlossaryEntry],
    query: str,
) -> GlossaryEntry | None:
    """Exact id or title match (case-insensitive), then id/title containment."""
    needle = normalize_glossary_query(query).casefold()
    if not needle:
        return None
    for entry in entries:
        if entry.id.casefold() == needle or entry.title.casefold() == needle:
            return entry
    for entry in entries:
        if needle in entry.id.casefold() or needle in entry.title.casefold():
            return entry
    return None
