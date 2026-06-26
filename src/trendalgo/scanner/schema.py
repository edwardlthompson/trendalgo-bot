"""Scanner SQLite schema (namespaced in scanner.db)."""

SCANNER_SCHEMA = """
CREATE TABLE IF NOT EXISTS scanner_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    interval_minutes INTEGER NOT NULL DEFAULT 60,
    min_volume_usd REAL NOT NULL DEFAULT 100000,
    min_gain_pct REAL NOT NULL DEFAULT 0.02,
    min_uniformity REAL NOT NULL DEFAULT 0.55,
    universe_filter TEXT NOT NULL DEFAULT 'kraken-spot',
    trendspotter_boost INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scanner_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1'
);

CREATE TABLE IF NOT EXISTS scanner_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    pair TEXT NOT NULL,
    uniformity REAL NOT NULL,
    gain_pct REAL NOT NULL,
    volume_score REAL NOT NULL,
    entry_signal INTEGER NOT NULL,
    sparkline_json TEXT NOT NULL,
    FOREIGN KEY (snapshot_id) REFERENCES scanner_snapshots(id)
);

CREATE TABLE IF NOT EXISTS scanner_watchlist (
    pair TEXT PRIMARY KEY,
    pinned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scanner_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tier TEXT NOT NULL,
    pair TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
