"""results.db DDL and schema version (ADR-0021)."""

from __future__ import annotations

SCHEMA_VERSION = 1
RESULTS_DB = "results.db"

DDL = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY NOT NULL,
  kind TEXT NOT NULL,
  lane TEXT NOT NULL DEFAULT '',
  pair TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL,
  finished_at TEXT,
  engine_version TEXT NOT NULL DEFAULT '',
  catalog_hash TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'running',
  params_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS opportunity_rows (
  run_id TEXT NOT NULL,
  row_id INTEGER NOT NULL,
  pair TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS strategy_rows (
  run_id TEXT NOT NULL,
  row_id INTEGER NOT NULL,
  strategy_id TEXT NOT NULL,
  pair TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL,
  PRIMARY KEY (run_id, row_id)
);

CREATE INDEX IF NOT EXISTS idx_opp_run ON opportunity_rows(run_id);
CREATE INDEX IF NOT EXISTS idx_strat_run ON strategy_rows(run_id);
CREATE INDEX IF NOT EXISTS idx_strat_pair ON strategy_rows(run_id, pair);

CREATE TABLE IF NOT EXISTS job_control (
  job_id TEXT PRIMARY KEY NOT NULL,
  run_id TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL DEFAULT 'idle',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS desk_commands (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT UNIQUE NOT NULL,
  action TEXT NOT NULL,
  lane TEXT NOT NULL DEFAULT 'crypto',
  status TEXT NOT NULL DEFAULT 'pending',
  params_json TEXT NOT NULL DEFAULT '{}',
  detail TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_desk_cmd_status ON desk_commands(status, seq);
"""
