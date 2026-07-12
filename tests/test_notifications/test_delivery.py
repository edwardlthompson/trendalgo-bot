from datetime import UTC, datetime
from pathlib import Path

from trendalgo.notifications.delivery import AlertDelivery
from trendalgo.notifications.preferences import NotificationPreferences, save_preferences
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.scanner.alerts import emit_alerts_for_snapshot
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore


class FailedTelegram:
    enabled = True
    calls = 0

    def send_message(self, _text: str) -> bool:
        self.calls += 1
        return False


def test_delivery_records_telegram_error_on_inbox_item(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    save_preferences(
        store,
        NotificationPreferences(scanner=True, push_enabled=True),
    )
    telegram = FailedTelegram()
    delivery = AlertDelivery(store, telegram=telegram)

    notification_id = delivery.deliver("scanner", "Tier A scanner alert", "BTC/USD")

    assert notification_id is not None
    assert telegram.calls == 1
    assert store.list_notifications()[0]["delivery_error"] == "telegram: delivery failed"


def test_scanner_emits_all_tiers_and_market_events(tmp_path: Path) -> None:
    scanner_store = ScannerStore(tmp_path / "scanner.db")
    now = datetime.now(UTC)
    snapshot = QualifiedSnapshot(
        generated_at=now,
        as_of=now,
        scan_id=1,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.8,
                gain_pct=0.06,
                volume_score=3,
                entry_signal=True,
            ),
            OpportunityRow(
                rank=2,
                pair="ETH/USD",
                uniformity=0.4,
                gain_pct=0.01,
                volume_score=1,
                entry_signal=False,
            ),
        ],
    )
    delivered: list[tuple[str, str, str]] = []

    emit_alerts_for_snapshot(
        scanner_store,
        snapshot,
        lambda category, title, body: delivered.append((category, title, body)),
    )

    scanner_titles = [title for category, title, _body in delivered if category == "scanner"]
    assert scanner_titles == ["Tier A scanner alert", "Tier C scanner alert"]
    assert any(category == "market" for category, _title, _body in delivered)
