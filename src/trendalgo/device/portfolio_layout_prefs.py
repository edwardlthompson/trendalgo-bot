"""Dashboard multi-page grid layout preferences (profile JSON)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from trendalgo.device.portfolio_module_catalog import (
    DEFAULT_PAGES,
    MODULE_IDS,
    effective_spec,
    spec_for,
)
from trendalgo.device.profile import ProfileError, read_json, write_json

PREFS_FILE = "portfolio_layout_prefs.json"
_COLS_MIN, _COLS_MAX = 4, 32
_ROWS_MIN, _ROWS_MAX = 4, 96
_GAP_MIN, _GAP_MAX = 4, 24
_MAGNET_MIN, _MAGNET_MAX = 4, 48


@dataclass
class Placement:
    id: str
    col: int = 0
    row: int = 0
    w: int = 8
    h: int = 3


@dataclass
class PageLayout:
    id: str
    name: str
    placements: list[Placement] = field(default_factory=list)


_LAYOUT_VERSION = 3


@dataclass
class GridPrefs:
    cols: int = 24
    rows: int = 24
    gap_px: int = 8
    magnet_px: int = 16
    show_grid: bool = False


@dataclass
class LayoutPrefs:
    active_page_id: str = "overview"
    grid: GridPrefs = field(default_factory=GridPrefs)
    pages: list[PageLayout] = field(default_factory=list)
    range: str = "1y"
    quote: str = "USD"
    assets_sort: str = "allocation_desc"
    layout_version: int = _LAYOUT_VERSION
    module_mins: dict[str, tuple[int, int]] = field(default_factory=dict)


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def factory_defaults() -> LayoutPrefs:
    pages = [
        PageLayout(
            id=p["id"],
            name=p["name"],
            placements=[Placement(**pl) for pl in p["placements"]],
        )
        for p in DEFAULT_PAGES
    ]
    return LayoutPrefs(active_page_id=pages[0].id if pages else "overview", pages=pages)


def load_prefs(root: Path) -> LayoutPrefs:
    try:
        raw = read_json(prefs_path(root))
    except ProfileError:
        return factory_defaults()
    if not isinstance(raw, dict):
        return factory_defaults()
    try:
        version = int(raw.get("layout_version") or 0)
    except (TypeError, ValueError):
        version = 0
    # Bump resets factory so sparse / 12-col grids do not stick after polish.
    if version < _LAYOUT_VERSION:
        return factory_defaults()
    try:
        return _parse(raw)
    except (TypeError, ValueError, KeyError):
        return factory_defaults()


def save_prefs(root: Path, prefs: LayoutPrefs) -> None:
    payload = asdict(prefs)
    # Serialize module_mins as {id: {min_w, min_h}} for readable JSON.
    payload["module_mins"] = {
        mid: {"min_w": wh[0], "min_h": wh[1]} for mid, wh in prefs.module_mins.items()
    }
    write_json(prefs_path(root), payload)


def active_page(prefs: LayoutPrefs) -> PageLayout:
    for page in prefs.pages:
        if page.id == prefs.active_page_id:
            return page
    if prefs.pages:
        return prefs.pages[0]
    return factory_defaults().pages[0]


def _parse(raw: dict[str, Any]) -> LayoutPrefs:
    grid_raw = raw.get("grid") if isinstance(raw.get("grid"), dict) else {}
    grid = GridPrefs(
        cols=_clamp(int(grid_raw.get("cols", 24)), _COLS_MIN, _COLS_MAX),
        rows=_clamp(int(grid_raw.get("rows", 24)), _ROWS_MIN, _ROWS_MAX),
        gap_px=_clamp(int(grid_raw.get("gap_px", 8)), _GAP_MIN, _GAP_MAX),
        magnet_px=_clamp(int(grid_raw.get("magnet_px", 16)), _MAGNET_MIN, _MAGNET_MAX),
        show_grid=bool(grid_raw.get("show_grid", False)),
    )
    module_mins = _parse_module_mins(raw.get("module_mins"))
    pages_raw = raw.get("pages")
    if not isinstance(pages_raw, list) or not pages_raw:
        return factory_defaults()
    pages: list[PageLayout] = []
    for item in pages_raw:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        name = str(item.get("name") or pid).strip() or pid
        if not pid:
            continue
        placements = _parse_placements(item.get("placements"), grid.cols, grid.rows, module_mins)
        pages.append(PageLayout(id=pid, name=name, placements=placements))
    if not pages:
        return factory_defaults()
    active = str(raw.get("active_page_id") or pages[0].id)
    if active not in {p.id for p in pages}:
        active = pages[0].id
    try:
        version = int(raw.get("layout_version") or _LAYOUT_VERSION)
    except (TypeError, ValueError):
        version = _LAYOUT_VERSION
    return LayoutPrefs(
        active_page_id=active,
        grid=grid,
        pages=pages,
        range=str(raw.get("range") or "1y"),
        quote=str(raw.get("quote") or "USD"),
        assets_sort=str(raw.get("assets_sort") or "allocation_desc"),
        layout_version=version,
        module_mins=module_mins,
    )


def _parse_module_mins(raw: Any) -> dict[str, tuple[int, int]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, tuple[int, int]] = {}
    for mid, val in raw.items():
        key = str(mid)
        if key not in MODULE_IDS:
            continue
        spec = spec_for(key)
        if spec is None:
            continue
        if isinstance(val, dict):
            min_w = int(val.get("min_w", spec.min_w))
            min_h = int(val.get("min_h", spec.min_h))
        elif isinstance(val, (list, tuple)) and len(val) >= 2:
            min_w, min_h = int(val[0]), int(val[1])
        else:
            continue
        out[key] = (
            _clamp(min_w, 1, spec.max_w),
            _clamp(min_h, 1, spec.max_h),
        )
    return out


def _parse_placements(
    raw: Any,
    cols: int,
    rows: int,
    module_mins: dict[str, tuple[int, int]],
) -> list[Placement]:
    del rows  # Canvas may grow rows; placements are not clipped to prefs.rows here.
    if not isinstance(raw, list):
        return []
    out: list[Placement] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        mid = str(item.get("id") or "").strip()
        if mid not in MODULE_IDS or mid in seen:
            continue
        spec = effective_spec(mid, module_mins) or spec_for(mid)
        min_w = spec.min_w if spec else 1
        min_h = spec.min_h if spec else 1
        max_w = min(cols, spec.max_w if spec else cols)
        max_h = spec.max_h if spec else 16
        w = _clamp(int(item.get("w", 8)), min_w, max_w)
        h = _clamp(int(item.get("h", 3)), min_h, max_h)
        col = _clamp(int(item.get("col", 0)), 0, max(0, cols - w))
        row = max(0, int(item.get("row", 0)))
        out.append(Placement(id=mid, col=col, row=row, w=w, h=h))
        seen.add(mid)
    return out


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))
