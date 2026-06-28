"""Icon registry SQLite schema."""

ICON_REGISTRY_SCHEMA = """
CREATE TABLE IF NOT EXISTS exchange_icons (
    id TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    color TEXT NOT NULL,
    icon_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coin_icons (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    coingecko_id TEXT NOT NULL,
    icon_url TEXT NOT NULL,
    market_cap_rank INTEGER
);
CREATE INDEX IF NOT EXISTS idx_coin_icons_rank ON coin_icons (market_cap_rank);
"""
