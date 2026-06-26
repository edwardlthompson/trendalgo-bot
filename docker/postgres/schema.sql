-- PostgreSQL mirror schema for TrendAlgo portfolio (Sprint 12)
-- TimescaleDB optional: hypertable on portfolio_snapshots when extension present

CREATE TABLE IF NOT EXISTS portfolio_accounts (
    id SERIAL PRIMARY KEY,
    exchange TEXT NOT NULL,
    label TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES portfolio_accounts(id),
    captured_at TIMESTAMPTZ NOT NULL,
    total_usd DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES portfolio_snapshots(id),
    asset TEXT NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    price_usd DOUBLE PRECISION NOT NULL,
    value_usd DOUBLE PRECISION NOT NULL,
    cost_basis_usd DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_account ON portfolio_snapshots(account_id, captured_at DESC);
