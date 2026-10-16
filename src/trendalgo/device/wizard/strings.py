"""Wizard screen copy (English). The guide text itself comes from content.py, not from here."""

from __future__ import annotations

APP_TITLE = "TrendAlgo setup wizard"
PROGRESS = "Step {number} of {total}: {title}"
CONTINUE = "Continue"
BACK = "Back"
SOURCES_HEADING = "Official sources"
SOURCE_LINE = "{label} ({url}), checked {checked}"
DONE_TITLE = "All setup steps are saved."
DONE_BODY = (
    "This wizard does not turn on live trading. The go-live checklist is a separate step "
    "that is not built yet."
)
SAVE_FAILED = "Your progress could not be saved: {reason}"
ACK = "I have read this step."
ACK_NEEDED = "Tick the box to confirm you have read this step."
PERMISSION_HELP = "Tick each permission you set on Kraken. Each tick confirms it is on."
WITHDRAW_CONFIRM = (
    "Withdraw Funds, Deposit Funds, and Export Data are unticked on Kraken. "
    "Withdraw Funds must stay off."
)
PRACTICE_NOTE = (
    "Practice mode starts the host on 127.0.0.1, runs four checks, and stops it. "
    "It places no orders and uses no exchange keys."
)
PRACTICE_PASSED = "Practice checks passed. You can continue."
CAPACITY_BUTTON = "Oracle says out of host capacity"
CAPACITY_TEXT = (
    "Try another availability domain, or wait and try again. If capacity stays short, "
    "choose Path B: a paid VPS on an amd64 or arm64 machine."
)
PAIR_NOTE = (
    "The host shows a pairing code once. Enter it within 10 minutes. The host must use the "
    "address set in Settings."
)
PAIR_HOST = "Host address"
PAIR_OWNER = "Owner secret"
PAIR_OWNER_HELP = (
    "The same owner secret the host uses. It is saved in Windows Credential Manager "
    "only after pairing succeeds."
)
PAIR_CODE = "Pairing code"
PAIR_CODE_HELP = "Shown once on the host. Dashes and spaces are fine."
OWNER_MISSING = "Save an owner ID in Settings first, then come back to this step."
