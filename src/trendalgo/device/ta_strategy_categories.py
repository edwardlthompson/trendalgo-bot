"""All-TA strategy category map (bundled JSON) + README <details> render."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from trendalgo.device.bundled_data import bundled_json

_CATS = "ta_strategy_categories.json"


@dataclass(frozen=True)
class StrategyCategory:
    id: str
    name: str
    strategies: tuple[str, ...]


def clear_strategy_category_cache() -> None:
    load_strategy_categories.cache_clear()


@lru_cache(maxsize=1)
def load_strategy_categories() -> tuple[StrategyCategory, ...]:
    raw = bundled_json(_CATS)
    out: list[StrategyCategory] = []
    for row in raw.get("categories") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or "").strip()
        name = str(row.get("name") or "").strip()
        ids = row.get("strategies") or []
        if not cid or not name or not isinstance(ids, list):
            continue
        strategies = tuple(sorted({str(x).strip().upper() for x in ids if str(x).strip()}))
        out.append(StrategyCategory(id=cid, name=name, strategies=strategies))
    return tuple(out)


def categorized_strategy_ids() -> frozenset[str]:
    ids: set[str] = set()
    for cat in load_strategy_categories():
        ids.update(cat.strategies)
    return frozenset(ids)


def render_readme_strategy_details() -> str:
    """GitHub-flavored collapsed lists for README (closed by default)."""
    cats = load_strategy_categories()
    total = sum(len(c.strategies) for c in cats)
    lines = [
        f"**{total}** indicators and patterns across the All-TA catalog. "
        "Expand a category to see every strategy id:",
        "",
    ]
    for cat in cats:
        n = len(cat.strategies)
        lines.append("<details>")
        lines.append(f"<summary>{cat.name} ({n})</summary>")
        lines.append("")
        lines.append(", ".join(f"`{s}`" for s in cat.strategies))
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
