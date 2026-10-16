"""Secrets for this PC, kept in Windows Credential Manager (row 19). Nothing writes them to a file.

The Windows binding uses ctypes (advapi32), so no package is added. It is looked up at run time,
so this module imports on any OS. Other systems get a refusal, never a silent memory store.
"""

from __future__ import annotations

import ctypes
import secrets
import sys
from typing import Any, Protocol

OWNER_SECRET_TARGET = "TrendAlgo/owner-secret"
PRACTICE_SECRET_TARGET = "TrendAlgo/practice-secret"
SECRET_BYTES = 32
_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_ERROR_NOT_FOUND = 1168


class CredentialError(RuntimeError):
    """The vault refused a call. The message names a Windows error code, never the secret."""


class CredentialStore(Protocol):
    def read(self, target: str) -> str | None: ...

    def write(self, target: str, secret: str) -> None: ...

    def delete(self, target: str) -> None: ...


class MemoryCredentialStore:
    """In-process store for tests. The app never uses it: nothing is kept after the process ends."""

    def __init__(self) -> None:
        self._items: dict[str, str] = {}

    def read(self, target: str) -> str | None:
        return self._items.get(target)

    def write(self, target: str, secret: str) -> None:
        self._items[target] = secret

    def delete(self, target: str) -> None:
        self._items.pop(target, None)


class _FileTime(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
        ("TargetName", ctypes.c_wchar_p),
        ("Comment", ctypes.c_wchar_p),
        ("LastWritten", _FileTime),
        ("CredentialBlobSize", ctypes.c_uint32),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", ctypes.c_uint32),
        ("AttributeCount", ctypes.c_uint32),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", ctypes.c_wchar_p),
        ("UserName", ctypes.c_wchar_p),
    ]


def _last_error() -> int:
    # Windows only. getattr keeps mypy quiet on other platforms, where typeshed omits the name.
    return int(getattr(ctypes, "get_last_error")())  # noqa: B009


class WindowsCredentialStore:
    """Generic credentials in Windows Credential Manager, scoped to this Windows account."""

    _lib: Any

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise CredentialError("Windows Credential Manager is only available on Windows.")
        win_dll: Any = getattr(ctypes, "WinDLL")  # noqa: B009 (Windows only, see _last_error)
        self._lib = win_dll("advapi32", use_last_error=True)
        self._lib.CredWriteW.argtypes = [ctypes.POINTER(_Credential), ctypes.c_uint32]
        self._lib.CredReadW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.POINTER(_Credential)),
        ]
        self._lib.CredDeleteW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
        self._lib.CredFree.argtypes = [ctypes.c_void_p]

    def read(self, target: str) -> str | None:
        found = ctypes.POINTER(_Credential)()
        if not self._lib.CredReadW(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(found)):
            code = _last_error()
            if code == _ERROR_NOT_FOUND:
                return None
            raise CredentialError(f"Credential Manager could not read it (Windows error {code}).")
        try:
            cred = found.contents
            if cred.CredentialBlobSize == 0:
                return ""
            raw = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
            return raw.decode("utf-8")
        finally:
            self._lib.CredFree(found)

    def write(self, target: str, secret: str) -> None:
        blob = secret.encode("utf-8")
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        cred = _Credential(
            Type=_CRED_TYPE_GENERIC,
            TargetName=target,
            CredentialBlobSize=len(blob),
            CredentialBlob=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
            Persist=_CRED_PERSIST_LOCAL_MACHINE,
        )
        if not self._lib.CredWriteW(ctypes.pointer(cred), 0):
            raise CredentialError(
                f"Credential Manager could not save it (Windows error {_last_error()})."
            )

    def delete(self, target: str) -> None:
        if not self._lib.CredDeleteW(target, _CRED_TYPE_GENERIC, 0):
            code = _last_error()
            if code != _ERROR_NOT_FOUND:
                raise CredentialError(
                    f"Credential Manager could not delete it (Windows error {code})."
                )


def open_store() -> CredentialStore:
    """The Windows vault. Other systems get a clear refusal."""
    return WindowsCredentialStore()


def get_or_create_secret(store: CredentialStore, target: str) -> str:
    """The stored secret, or a fresh random one saved under target."""
    existing = store.read(target)
    if existing:
        return existing
    fresh = secrets.token_urlsafe(SECRET_BYTES)
    store.write(target, fresh)
    return fresh
