"""Billing SQLite schema (Sprint 10)."""

BILLING_SCHEMA = """
CREATE TABLE IF NOT EXISTS license_enrollment (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enrolled INTEGER NOT NULL DEFAULT 0,
    license_rate_pct REAL NOT NULL DEFAULT 0.05,
    tier TEXT NOT NULL DEFAULT 'free',
    terms_version TEXT,
    install_uuid TEXT,
    enrolled_at TEXT,
    first_profitable_trade_at TEXT,
    billing_starts_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS terms_acceptance_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    terms_version TEXT NOT NULL,
    install_uuid TEXT NOT NULL,
    accepted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fee_ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_ref TEXT NOT NULL UNIQUE,
    period TEXT NOT NULL,
    pair TEXT NOT NULL,
    gross_profit_usd REAL NOT NULL,
    license_fee_usd REAL NOT NULL,
    net_benefit_usd REAL NOT NULL,
    rule_applied TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS license_statements (
    period TEXT PRIMARY KEY,
    gross_profit_usd REAL NOT NULL,
    license_fee_usd REAL NOT NULL,
    carry_forward_credit_usd REAL NOT NULL DEFAULT 0,
    net_loss_note TEXT,
    signed_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS license_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    grace_started_at TEXT,
    grace_day INTEGER NOT NULL DEFAULT 0,
    suspended INTEGER NOT NULL DEFAULT 0,
    unpaid_period TEXT,
    licensed_until TEXT,
    last_payment_id TEXT,
    last_tx_hash TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settlement_payments (
    id TEXT PRIMARY KEY,
    period TEXT NOT NULL,
    install_uuid TEXT NOT NULL,
    amount_usd REAL NOT NULL,
    amount_sats INTEGER NOT NULL DEFAULT 0,
    amount_btc REAL NOT NULL DEFAULT 0,
    amount_atomic INTEGER NOT NULL DEFAULT 0,
    asset TEXT NOT NULL DEFAULT 'BTC',
    chain TEXT NOT NULL DEFAULT 'bitcoin',
    chain_id INTEGER,
    token_contract TEXT,
    watch_from_block INTEGER,
    payment_reference TEXT NOT NULL,
    receipt_id TEXT NOT NULL,
    verification_hash TEXT NOT NULL,
    address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    tx_hash TEXT,
    confirmations INTEGER NOT NULL DEFAULT 0,
    licensed_until TEXT,
    created_at TEXT NOT NULL,
    confirmed_at TEXT,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_settlement_payments_status
    ON settlement_payments(status, created_at);

CREATE TABLE IF NOT EXISTS billing_milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    milestone_usd REAL NOT NULL,
    reached_at TEXT NOT NULL,
    notified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS carry_forward_credits (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    credit_usd REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""

CURRENT_TERMS_VERSION = "2026-06-draft-1"
DEFAULT_LICENSE_RATE = 0.05
GRACE_PERIOD_DAYS = 7
BILLING_START_DELAY_MONTHS = 1
