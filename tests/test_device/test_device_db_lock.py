"""Device databases use WAL and a busy timeout (D3). One profile lock admits one window."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import closing
from pathlib import Path

import pytest

from trendalgo.device.db import BUSY_TIMEOUT_S, connect, enable_wal
from trendalgo.device.lock import ProfileBusyError, ProfileLock

WRITES_PER_WRITER = 300


def test_enable_wal_switches_a_database_and_the_mode_persists(tmp_path: Path) -> None:
    path = tmp_path / "scanner.db"
    assert enable_wal(path) == "wal"
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_connect_waits_for_a_lock_instead_of_failing_at_once(tmp_path: Path) -> None:
    with closing(connect(tmp_path / "x.db")) as conn:
        timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert timeout_ms == int(BUSY_TIMEOUT_S * 1000)


def test_two_writers_on_one_wal_database_lose_no_rows(tmp_path: Path) -> None:
    """Smoke test: two connections write at the same time. Each write waits its turn; none fails."""
    path = tmp_path / "scanner.db"
    assert enable_wal(path) == "wal"
    with closing(connect(path)) as setup:
        setup.execute("CREATE TABLE writes (writer INTEGER, n INTEGER)")
        setup.commit()
    errors: list[sqlite3.Error] = []

    def write(writer: int) -> None:
        try:
            with closing(connect(path)) as conn:
                for n in range(WRITES_PER_WRITER):
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("INSERT INTO writes VALUES (?, ?)", (writer, n))
                    conn.commit()
        except sqlite3.Error as exc:
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(writer,)) for writer in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    with closing(connect(path)) as check:
        rows = check.execute("SELECT COUNT(*) FROM writes").fetchone()[0]
    assert rows == 2 * WRITES_PER_WRITER


def test_a_second_lock_on_the_same_profile_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "device.lock"
    first = ProfileLock(path)
    first.acquire()
    try:
        rival = ProfileLock(path)
        with pytest.raises(ProfileBusyError, match="Another TrendAlgo window"):
            rival.acquire()
    finally:
        first.release()


def test_the_lock_is_free_again_after_release(tmp_path: Path) -> None:
    path = tmp_path / "device.lock"
    with ProfileLock(path):
        pass
    with ProfileLock(path):
        pass


def test_releasing_twice_is_harmless(tmp_path: Path) -> None:
    lock = ProfileLock(tmp_path / "device.lock")
    lock.acquire()
    lock.release()
    lock.release()
