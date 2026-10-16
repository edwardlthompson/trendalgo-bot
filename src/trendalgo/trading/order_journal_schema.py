"""Schema and column list for the order journal (E2, E3)."""

from __future__ import annotations

ORDER_COLUMNS = (
    "client_id",
    "exchange",
    "pair",
    "side",
    "amount",
    "status",
    "exchange_order_id",
    "detail",
    "created_at",
    "filled",
)
ORDER_SELECT = "SELECT " + ", ".join(ORDER_COLUMNS) + " FROM orders"
SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    client_id TEXT PRIMARY KEY,
    exchange TEXT NOT NULL,
    pair TEXT NOT NULL,
    side TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    exchange_order_id TEXT,
    detail TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    filled REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS exchange_guard (
    exchange TEXT PRIMARY KEY,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    halted INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    announced INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS balance_checkpoints (
    exchange TEXT NOT NULL,
    asset TEXT NOT NULL,
    total REAL NOT NULL,
    applied REAL NOT NULL,
    checked_at REAL NOT NULL,
    PRIMARY KEY (exchange, asset)
);
"""
