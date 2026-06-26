"""Portfolio + notification SQLite schema (Sprint 4–5)."""

from __future__ import annotations

PORTFOLIO_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    captured_at TEXT NOT NULL,
    total_usd REAL NOT NULL,
    source TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES portfolio_accounts(id)
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    asset TEXT NOT NULL,
    quantity REAL NOT NULL,
    price_usd REAL NOT NULL,
    value_usd REAL NOT NULL,
    cost_basis_usd REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots(id)
);

CREATE TABLE IF NOT EXISTS portfolio_daily_aggregates (
    account_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    total_usd REAL NOT NULL,
    daily_pnl_usd REAL NOT NULL DEFAULT 0,
    realized_pnl_usd REAL NOT NULL DEFAULT 0,
    unrealized_pnl_usd REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (account_id, date),
    FOREIGN KEY (account_id) REFERENCES portfolio_accounts(id)
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    trades INTEGER NOT NULL DEFAULT 1,
    pnl_swings INTEGER NOT NULL DEFAULT 1,
    fees INTEGER NOT NULL DEFAULT 1,
    scanner INTEGER NOT NULL DEFAULT 0,
    push_enabled INTEGER NOT NULL DEFAULT 0,
    quiet_hours_start TEXT,
    quiet_hours_end TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS webhook_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    accepted INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_accounts_meta (
    account_id INTEGER PRIMARY KEY,
    account_type TEXT NOT NULL DEFAULT 'spot',
    FOREIGN KEY (account_id) REFERENCES portfolio_accounts(id)
);

CREATE TABLE IF NOT EXISTS asset_tags (
    asset TEXT PRIMARY KEY,
    tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS manual_cost_basis (
    account_id INTEGER NOT NULL,
    asset TEXT NOT NULL,
    cost_basis_usd REAL NOT NULL,
    PRIMARY KEY (account_id, asset),
    FOREIGN KEY (account_id) REFERENCES portfolio_accounts(id)
);

CREATE TABLE IF NOT EXISTS allocation_targets (
    account_id INTEGER NOT NULL,
    asset TEXT NOT NULL,
    target_pct REAL NOT NULL,
    PRIMARY KEY (account_id, asset),
    FOREIGN KEY (account_id) REFERENCES portfolio_accounts(id)
);

CREATE TABLE IF NOT EXISTS performance_goals (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    target_net_worth_usd REAL NOT NULL DEFAULT 2000,
    deadline TEXT,
    label TEXT NOT NULL DEFAULT 'Growth goal',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS basket_allocation (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    weights_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS public_dashboard_shares (
    token TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
"""
