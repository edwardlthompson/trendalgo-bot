"""One writer per profile (D3): an OS file lock stops a second app window on the same folder."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BUSY_MESSAGE = "Another TrendAlgo window is using this profile. Close it, then start again."


class ProfileBusyError(RuntimeError):
    """Another window holds the profile folder's lock."""


class ProfileLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        """True while this object holds the profile lock (the wizard checks it before a save)."""
        return self._fd is not None

    def acquire(self) -> None:
        if self._fd is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            _lock_fd(fd)
        except OSError as exc:
            os.close(fd)
            raise ProfileBusyError(BUSY_MESSAGE) from exc
        self._fd = fd

    def release(self) -> None:
        fd, self._fd = self._fd, None
        if fd is not None:
            try:
                _unlock_fd(fd)
            finally:
                os.close(fd)

    def __enter__(self) -> ProfileLock:
        self.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()


def _lock_fd(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_fd(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
