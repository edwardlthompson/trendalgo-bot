"""TradFi / Forex board icons (disk cache + lettermark / FX composite fallbacks)."""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty, SimpleQueue

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap

from trendalgo.device.coin_icons import coin_icon_path

# Public PNG logos by US ticker (no API key). Clearbit needs domains — unusable here.
_LOGO_URLS = (
    "https://financialmodelingprep.com/image-stock/{symbol}.png",
    "https://images.financialmodelingprep.com/symbol/{symbol}.png",
)
_HTTP_TIMEOUT_S = 8
_FETCH_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lane-icon")
_FX_POOL_SEEDED = False


def icon_cache_dir(root: Path) -> Path:
    path = root / "icon_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def equity_cache_path(root: Path, symbol: str) -> Path:
    sym = (symbol or "").strip().upper().split("/")[0]
    return icon_cache_dir(root) / f"eq_{sym}.png"


def icon_for_row(
    root: Path,
    symbol: str,
    *,
    lane: str = "crypto",
    pair: str = "",
    size: int = 36,
    fetch_remote: bool = False,
) -> QPixmap:
    """Return a pixmap for the board logo cell (never blocks unless fetch_remote)."""
    key = (lane or "crypto").strip().lower()
    sym = (symbol or "").strip().upper().split("/")[0]
    if key == "crypto":
        path = coin_icon_path(sym)
        if path is not None:
            pix = QPixmap(str(path))
            if not pix.isNull():
                return _scaled(pix, size)
        return _lettermark(sym or "?", size)
    if key == "forex":
        global _FX_POOL_SEEDED
        if not _FX_POOL_SEEDED:
            from trendalgo.device.currency_icons import ensure_universe_currency_icons

            ensure_universe_currency_icons(size=max(64, size))
            _FX_POOL_SEEDED = True
        return _fx_mark(pair or symbol, size=size, root=root)
    cached = equity_cache_path(root, sym)
    if cached.is_file():
        pix = QPixmap(str(cached))
        if not pix.isNull():
            return _scaled(pix, size)
    if fetch_remote and sym:
        fetched = _fetch_equity_logo(sym, cached)
        if fetched is not None:
            return _scaled(fetched, size)
    return _lettermark(sym or "?", size)


def prefetch_equity_logo(root: Path, symbol: str) -> Path | None:
    """Blocking fetch for a worker thread; returns cache path when successful.

    Must not touch QPixmap — Qt pixmaps are not safe off the GUI thread.
    """
    sym = (symbol or "").strip().upper().split("/")[0]
    if not sym:
        return None
    cached = equity_cache_path(root, sym)
    if cached.is_file() and cached.stat().st_size > 32:
        return cached
    return cached if _download_equity_logo(sym, cached) else None


class EquityIconFetcher(QObject):
    """Background equity logo downloads; emits when a ticker is ready on disk."""

    ready = Signal(str)  # symbol

    def __init__(self, root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._root = root
        self._inflight: set[str] = set()
        self._done: SimpleQueue[str] = SimpleQueue()
        self._pump = QTimer(self)
        self._pump.setInterval(100)
        self._pump.timeout.connect(self._drain)
        self._pump.start()

    def request(self, symbols: list[str]) -> None:
        for raw in symbols:
            sym = (raw or "").strip().upper().split("/")[0]
            if not sym or sym in self._inflight:
                continue
            cached = equity_cache_path(self._root, sym)
            if cached.is_file() and cached.stat().st_size > 32:
                self.ready.emit(sym)
                continue
            self._inflight.add(sym)
            _FETCH_POOL.submit(self._work, sym)

    def _work(self, symbol: str) -> None:
        try:
            path = prefetch_equity_logo(self._root, symbol)
            if path is not None:
                self._done.put(symbol)
        finally:
            self._inflight.discard(symbol)

    def _drain(self) -> None:
        while True:
            try:
                symbol = self._done.get_nowait()
            except Empty:
                return
            self.ready.emit(symbol)


def _download_equity_logo(symbol: str, dest: Path) -> bool:
    """Write a PNG to ``dest``. Safe for worker threads (no QPixmap)."""
    for template in _LOGO_URLS:
        url = template.format(symbol=symbol.upper())
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TrendAlgoDevice/1.0"})
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:  # noqa: S310
                data = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
        if not data or len(data) < 32 or data[:4] != b"\x89PNG":
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest.is_file() and dest.stat().st_size > 32
    return False


def _fetch_equity_logo(symbol: str, dest: Path) -> QPixmap | None:
    """GUI-thread helper: download (if needed) and load a pixmap."""
    if not dest.is_file() or dest.stat().st_size <= 32:
        if not _download_equity_logo(symbol, dest):
            return None
    pix = QPixmap(str(dest))
    return None if pix.isNull() else pix


def _scaled(pix: QPixmap, size: int) -> QPixmap:
    return pix.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _lettermark(text: str, size: int) -> QPixmap:
    label = (text or "?")[:4]
    seed = int(hashlib.md5(label.encode(), usedforsecurity=False).hexdigest()[:6], 16)
    # Prefer mid-luminance colors so marks stay visible on dark UI.
    r = 80 + ((seed >> 16) & 127)
    g = 80 + ((seed >> 8) & 127)
    b = 80 + (seed & 127)
    bg = QColor(r, g, b)
    fg = QColor(255, 255, 255)
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(bg)
    painter.setPen(QColor(255, 255, 255, 40))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 6, 6)
    painter.setPen(fg)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(9, size // 3 - (1 if len(label) > 3 else 0)))
    painter.setFont(font)
    painter.drawText(pix.rect(), int(Qt.AlignmentFlag.AlignCenter), label)
    painter.end()
    return pix


def _fx_mark(pair: str, *, size: int, root: Path) -> QPixmap:
    raw = (pair or "").upper().replace("-", "/")
    if "/" in raw:
        base, quote = raw.split("/", 1)
    elif len(raw) >= 6 and raw.isalpha():
        base, quote = raw[:3], raw[3:6]
    else:
        base, quote = raw[:3], "USD"
    base, quote = (base[:3] or "??"), (quote[:3] or "USD")
    cache = icon_cache_dir(root) / f"fx_{base}_{quote}_{size}.png"
    if cache.is_file() and cache.stat().st_size > 32:
        pix = QPixmap(str(cache))
        if not pix.isNull():
            return pix
    left = _currency_pix(base, size)
    right = _currency_pix(quote, size)
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    half = size // 2 + 2
    painter.drawPixmap(
        0,
        0,
        left.scaled(
            half,
            half,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ),
    )
    painter.drawPixmap(
        size // 2 - 2,
        size // 2 - 2,
        right.scaled(
            half,
            half,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ),
    )
    painter.end()
    out.save(str(cache), "PNG")
    return out


def _currency_pix(code: str, size: int) -> QPixmap:
    from trendalgo.device.currency_icons import currency_icon_path, ensure_currency_icon

    path = currency_icon_path(code) or ensure_currency_icon(code, size=max(64, size))
    if path is not None:
        pix = QPixmap(str(path))
        if not pix.isNull():
            return pix
    return _lettermark(code or "??", size)
