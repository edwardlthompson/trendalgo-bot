"""Scanner page (D-02) on the Qt offscreen platform: Run scan, Cancel, the newer-source rule, and failures.

The worker is replaced by a fake pool, so these tests run in-process, stay offline, and spawn nothing.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.context import DeviceContext, open_context  # noqa: E402
from trendalgo.device.profile import DATA_ENV  # noqa: E402
from trendalgo.device.scan_job import scan_job  # noqa: E402
from trendalgo.device.scan_model import ScanUnavailableError  # noqa: E402
from trendalgo.device.scan_offline import offline_listings, offline_market  # noqa: E402
from trendalgo.device.views.scanner_page import ScannerPage  # noqa: E402
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot  # noqa: E402
from trendalgo.scanner.store import ScannerStore  # noqa: E402


class _Done:
    """A worker job that is ready at once and returns a value or raises an error."""

    def __init__(self, value: Any = None, error: BaseException | None = None) -> None:
        self._value = value
        self._error = error

    def ready(self) -> bool:
        return True

    def get(self, timeout: float | None = None) -> Any:
        if self._error is not None:
            raise self._error
        return self._value


class _Running:
    """A worker job that has not finished."""

    def ready(self) -> bool:
        return False

    def get(self, timeout: float | None = None) -> Any:
        raise TimeoutError("still running")


class _FakePool:
    def __init__(self, job: Any) -> None:
        self._job = job
        self.cancelled = False

    def submit(self, fn: Any, *args: Any) -> Any:
        return self._job

    def cancel(self) -> None:
        self.cancelled = True


def _snapshot(generated: datetime) -> QualifiedSnapshot:
    return QualifiedSnapshot(
        generated_at=generated,
        as_of=generated,
        scan_id=1,
        degraded=False,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.9,
                gain_pct=2.5,
                volume_score=10.0,
                entry_signal=True,
                sparkline=[0.0, 1.0],
            )
        ],
    )


def test_a_finished_scan_is_shown_as_scanned_on_this_pc(
    qtbot: QtBot,
    ctx: DeviceContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with offline_listings():
        result = scan_job(ctx.root, fetcher=offline_market)
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    monkeypatch.setattr(page, "_pool", _FakePool(_Done(result)))
    page._run.click()
    qtbot.waitUntil(lambda: page._pending is None, timeout=5000)
    assert page._status.text() == S.SCAN_DONE
    assert S.SCANNER_FROM_PC in page._caption.text()


def test_while_a_scan_runs_only_cancel_is_enabled_and_cancel_stops_the_pool(
    qtbot: QtBot,
    ctx: DeviceContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    pool = _FakePool(_Running())
    monkeypatch.setattr(page, "_pool", pool)
    page._run.click()
    assert not page._run.isEnabled()
    assert page._cancel.isEnabled()
    page._cancel.click()
    assert pool.cancelled
    assert page._pending is None
    assert page._run.isEnabled()
    assert not page._cancel.isEnabled()
    assert page._status.text() == S.SCAN_CANCELLED


def test_an_unavailable_scan_keeps_the_last_saved_scan_and_says_so(
    qtbot: QtBot,
    ctx: DeviceContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    monkeypatch.setattr(page, "_pool", _FakePool(_Done(error=ScanUnavailableError("no pair list"))))
    page._run.click()
    qtbot.waitUntil(lambda: page._pending is None, timeout=5000)
    assert S.SCAN_UNAVAILABLE in page._problem.text()
    assert page._run.isEnabled()


def test_a_scan_that_raises_says_it_did_not_finish(
    qtbot: QtBot,
    ctx: DeviceContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    monkeypatch.setattr(page, "_pool", _FakePool(_Done(error=RuntimeError("worker crashed"))))
    page._run.click()
    qtbot.waitUntil(lambda: page._pending is None, timeout=5000)
    assert S.SCAN_FAILED in page._problem.text()


def test_the_newer_of_the_bot_scan_and_this_pc_scan_is_shown_and_named(
    qtbot: QtBot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = tmp_path / "data"
    now = datetime.now(UTC)
    ScannerStore(shared / "scanner.db").save_snapshot(_snapshot(now - timedelta(days=1)))
    monkeypatch.setenv(DATA_ENV, str(shared))
    ctx = open_context(tmp_path / "profile")
    ScannerStore(ctx.root / "scanner.db").save_snapshot(_snapshot(now))
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    assert S.SCANNER_FROM_PC in page._caption.text()
    ScannerStore(shared / "scanner.db").save_snapshot(_snapshot(now + timedelta(days=1)))
    page.reload()
    assert S.SCANNER_FROM_BOT in page._caption.text()


def test_scanner_page_has_progress_bar(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    assert page._bar.minimum() == 0
    assert page._bar.maximum() == 100
    assert page._bar.value() == 0


def test_scanner_page_has_pwa_filter_strip_and_compare_clear(
    qtbot: QtBot,
    ctx: DeviceContext,
) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    assert page._filters.exchange.count() >= 3
    assert page._col_filters.gain_7d.suffix() == "%"
    assert page._col_filters.gain_30d.placeholderText() == "min%"
    page._compare.add("BTC/USD")
    page._compare.add("ETH/USD")
    page._show_tab()
    page._filters.clear_btn.click()
    assert page._compare == set()
    assert page._filters.share.objectName() == "shareButton"
    assert page._filters.share.toolTip() == S.SCANNER_SHARE_TIP


def test_filter_bar_keeps_zero_gains_as_integers(qtbot: QtBot) -> None:
    from trendalgo.device.views.scanner_column_filter_row import GainMinEdit, ScannerColumnFilterRow
    from trendalgo.device.views.scanner_filters import ScannerFilterBar

    actions = ScannerFilterBar()
    cols = ScannerColumnFilterRow()
    qtbot.addWidget(actions)
    qtbot.addWidget(cols)
    cols.load({"min_gain_pct": 30})  # legacy only — must not force 7d back to 30
    assert actions.vol.decimals() == 0
    assert isinstance(cols.gain_7d, GainMinEdit)
    assert cols.gain_7d.value() == 0
    assert cols.gain_30d.value() == 30
    cols.gain_7d.setValue(0)
    cols.gain_30d.setValue(0)
    actions.vol.setValue(500_000)
    saved = {**actions.dump(), **cols.dump()}
    assert saved["min_gain_7d"] == 0.0
    assert saved["min_gain_30d"] == 0.0
    assert saved["min_volume_usd"] == 500_000.0
    cols.load(saved)
    assert cols.gain_7d.value() == 0
    assert cols.gain_30d.value() == 0
