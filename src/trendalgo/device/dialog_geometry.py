"""Persist dialog size / maximized state by id under the device profile."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget

from trendalgo.device.profile import read_json, write_json

_FILE = "dialog_geometry.json"
_MIN_W = 480
_MIN_H = 320


def _path(root: Path) -> Path:
    return root / _FILE


def load_dialog_geometry(root: Path, dialog_id: str) -> dict[str, Any] | None:
    raw = read_json(_path(root))
    if not isinstance(raw, dict):
        return None
    block = raw.get(dialog_id)
    return dict(block) if isinstance(block, dict) else None


def save_dialog_geometry(
    root: Path,
    dialog_id: str,
    *,
    width: int,
    height: int,
    maximized: bool,
) -> None:
    path = _path(root)
    prior = read_json(path)
    payload: dict[str, Any] = dict(prior) if isinstance(prior, dict) else {}
    payload[dialog_id] = {
        "width": max(_MIN_W, int(width)),
        "height": max(_MIN_H, int(height)),
        "maximized": bool(maximized),
    }
    write_json(path, payload)


def enable_minmax(dialog: QDialog) -> None:
    dialog.setWindowFlags(
        dialog.windowFlags()
        | Qt.WindowType.Window
        | Qt.WindowType.WindowMinMaxButtonsHint
        | Qt.WindowType.WindowCloseButtonHint
    )


def restore_dialog_geometry(
    root: Path,
    dialog: QWidget,
    dialog_id: str,
    *,
    default_w: int = 900,
    default_h: int = 640,
) -> None:
    block = load_dialog_geometry(root, dialog_id)
    if block is None:
        dialog.resize(max(_MIN_W, default_w), max(_MIN_H, default_h))
        return
    w = max(_MIN_W, int(block.get("width") or default_w))
    h = max(_MIN_H, int(block.get("height") or default_h))
    dialog.resize(w, h)
    if bool(block.get("maximized")):
        dialog.showMaximized()


def bind_dialog_geometry(root: Path, dialog: QDialog, dialog_id: str) -> None:
    """Save size/maximize when the dialog finishes."""

    def _persist(_result: int = 0) -> None:
        maximized = bool(dialog.isMaximized())
        if maximized:
            # Keep last normal size already stored if any; update maximize flag.
            prior = load_dialog_geometry(root, dialog_id) or {}
            save_dialog_geometry(
                root,
                dialog_id,
                width=int(prior.get("width") or max(_MIN_W, dialog.width())),
                height=int(prior.get("height") or max(_MIN_H, dialog.height())),
                maximized=True,
            )
            return
        save_dialog_geometry(
            root,
            dialog_id,
            width=dialog.width(),
            height=dialog.height(),
            maximized=False,
        )

    dialog.finished.connect(_persist)
