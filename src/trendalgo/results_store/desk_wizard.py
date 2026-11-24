"""Setup wizard W0–W5 surface for Avalonia (AV-G-SET6)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.lock import ProfileBusyError, ProfileLock
from trendalgo.device.profile import LOCK_FILE, SETTINGS_FILE, ProfileError, read_json
from trendalgo.device.settings_model import settings_from_document
from trendalgo.device.wizard import strings as W
from trendalgo.device.wizard.content import STEPS
from trendalgo.device.wizard.credentials import MemoryCredentialStore, WindowsCredentialStore
from trendalgo.device.wizard.hostclient import pair_host
from trendalgo.device.wizard.practice import run_practice
from trendalgo.device.wizard.state import (
    STEP_IDS,
    WIZARD_FILE,
    WizardError,
    WizardState,
    advance,
    load_state,
    save_state,
)
from trendalgo.device.wizard.validators import (
    PERMISSIONS,
    Problem,
    check_key_permissions,
)

__all__ = ["advance_wizard", "load_wizard_surface", "rewind_wizard"]

_ACK_STEPS = frozenset({"W0", "W3", "W5"})


def load_wizard_surface(root: Path) -> dict[str, Any]:
    path = root / WIZARD_FILE
    try:
        state = load_state(path)
    except ProfileError as exc:
        return {
            "ok": False,
            "error": "bad_state",
            "problems": [str(exc)],
            "done": [],
            "complete": False,
        }
    return _view(root, state)


def rewind_wizard(root: Path) -> dict[str, Any]:
    path = root / WIZARD_FILE
    try:
        state = load_state(path)
    except ProfileError as exc:
        return {"ok": False, "error": "bad_state", "problems": [str(exc)]}
    if not state.done:
        return {"ok": False, "error": "nothing_to_rewind", "problems": ["no finished step"]}
    try:
        state = state.rewind()
        _persist(root, state)
    except (WizardError, ProfileBusyError, OSError) as exc:
        return {"ok": False, "error": "save_failed", "problems": [str(exc)]}
    out = _view(root, state)
    out["ok"] = True
    return out


def advance_wizard(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path = root / WIZARD_FILE
    try:
        state = load_state(path)
    except ProfileError as exc:
        return {"ok": False, "error": "bad_state", "problems": [str(exc)]}
    step_id = state.next_step()
    if step_id is None:
        out = _view(root, state)
        out["ok"] = True
        return out
    problems = _checks(root, step_id, payload)
    state, blocked = advance(state, step_id, problems)
    if blocked:
        return {
            "ok": False,
            "error": "validation",
            "problems": [p.message for p in blocked],
            "step_id": step_id,
            **{k: v for k, v in _view(root, state).items() if k != "ok"},
        }
    try:
        _persist(root, state)
    except (WizardError, ProfileBusyError, OSError) as exc:
        return {"ok": False, "error": "save_failed", "problems": [str(exc)]}
    out = _view(root, state)
    out["ok"] = True
    return out


def _persist(root: Path, state: WizardState) -> None:
    lock = ProfileLock(root / LOCK_FILE)
    lock.acquire()
    try:
        save_state(root / WIZARD_FILE, state, lock)
    finally:
        lock.release()


def _view(root: Path, state: WizardState) -> dict[str, Any]:
    step_id = state.next_step()
    base: dict[str, Any] = {
        "ok": True,
        "done": list(state.done),
        "complete": step_id is None,
        "total": len(STEP_IDS),
        "ack_label": W.ACK,
        "continue_label": W.CONTINUE,
        "back_label": W.BACK,
        "permissions": list(PERMISSIONS),
        "withdraw_label": W.WITHDRAW_CONFIRM,
        "permission_help": W.PERMISSION_HELP,
        "practice_note": W.PRACTICE_NOTE,
        "pair_note": W.PAIR_NOTE,
        "pair_host_label": W.PAIR_HOST,
        "pair_secret_label": W.PAIR_OWNER,
        "pair_secret_help": W.PAIR_OWNER_HELP,
        "pair_code_label": W.PAIR_CODE,
        "pair_code_help": W.PAIR_CODE_HELP,
        "capacity_help": W.CAPACITY_TEXT,
    }
    if step_id is None:
        base.update(
            {
                "step_id": None,
                "number": len(STEP_IDS),
                "title": W.DONE_TITLE,
                "body": [W.DONE_BODY],
                "sources": [],
                "kind": "done",
                "progress": W.DONE_TITLE,
            }
        )
        return base
    step = next(item for item in STEPS if item.step_id == step_id)
    number = STEP_IDS.index(step_id) + 1
    kind = _kind(step_id)
    owner_id, host_url = _saved_host(root)
    base.update(
        {
            "step_id": step_id,
            "number": number,
            "title": step.title,
            "body": list(step.body),
            "sources": [
                {
                    "label": s.label,
                    "url": s.url,
                    "checked": s.verified.isoformat(),
                }
                for s in step.sources
            ],
            "kind": kind,
            "progress": W.PROGRESS.format(number=number, total=len(STEP_IDS), title=step.title),
            "owner_id": owner_id or "",
            "host_url": host_url,
            "can_back": bool(state.done),
        }
    )
    return base


def _kind(step_id: str) -> str:
    if step_id in _ACK_STEPS:
        return "ack"
    if step_id == "W1":
        return "keys"
    if step_id == "W2":
        return "practice"
    if step_id == "W4":
        return "pair"
    return "ack"


def _saved_host(root: Path) -> tuple[str | None, str]:
    try:
        settings = settings_from_document(read_json(root / SETTINGS_FILE))
    except ProfileError:
        return None, ""
    if settings is None:
        return None, ""
    return settings.owner_id, settings.host_url


def _checks(root: Path, step_id: str, payload: dict[str, Any]) -> list[Problem]:
    if step_id in _ACK_STEPS:
        if not bool(payload.get("ack")):
            return [Problem("step.not_acknowledged", W.ACK_NEEDED)]
        return []
    if step_id == "W1":
        raw = payload.get("permissions") or []
        ticked = frozenset(str(x) for x in raw) if isinstance(raw, list) else frozenset()
        problem = check_key_permissions(ticked, bool(payload.get("withdraw_off")))
        return [] if problem is None else [problem]
    if step_id == "W2":
        store = _store()
        return run_practice(root, store)
    if step_id == "W4":
        owner_id, _ = _saved_host(root)
        if owner_id is None:
            return [Problem("owner.missing", W.OWNER_MISSING)]
        return pair_host(
            str(payload.get("host_url") or ""),
            owner_id,
            str(payload.get("owner_secret") or ""),
            str(payload.get("pairing_code") or ""),
            _store(),
        )
    return [Problem("step.unknown", f"Unknown step {step_id}")]


def _store() -> Any:
    import os

    if os.environ.get("TRENDALGO_WIZARD_MEMORY") == "1":
        return MemoryCredentialStore()
    try:
        return WindowsCredentialStore()
    except Exception:
        return MemoryCredentialStore()
