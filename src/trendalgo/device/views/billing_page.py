"""Billing and Growth shell (ADR-0017): owner-only copy, settlement and referrals disabled."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.views.widgets import page_header, section_title


class BillingPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        owner = QLabel(S.BILLING_OWNER_BODY)
        owner.setWordWrap(True)
        owner.setObjectName("hint")
        settle = QPushButton(S.BILLING_SETTLEMENT)
        settle.setEnabled(False)
        settle.setToolTip(S.BILLING_SETTLEMENT_HELP)
        settle_help = QLabel(S.BILLING_SETTLEMENT_HELP)
        settle_help.setWordWrap(True)
        settle_help.setObjectName("hint")
        referrals = QPushButton(S.BILLING_REFERRALS)
        referrals.setEnabled(False)
        referrals.setToolTip(S.BILLING_REFERRALS_HELP)
        referrals_help = QLabel(S.BILLING_REFERRALS_HELP)
        referrals_help.setWordWrap(True)
        referrals_help.setObjectName("hint")
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.BILLING_TITLE, S.BILLING_SUBTITLE))
        layout.addWidget(section_title(S.BILLING_OWNER_SECTION))
        layout.addWidget(owner)
        layout.addWidget(settle, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(settle_help)
        layout.addWidget(section_title(S.BILLING_GROWTH))
        layout.addWidget(referrals, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(referrals_help)
        layout.addStretch(1)
