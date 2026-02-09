PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS memory_items (
  id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  kind TEXT NOT NULL,
  key TEXT,
  text TEXT NOT NULL,
  data TEXT,
  source TEXT NOT NULL,
  confidence REAL NOT NULL,
  created_at TEXT NOT NULL,
  ttl_seconds INTEGER,
  trace_id TEXT NOT NULL,
  approval_ref TEXT,
  tags TEXT,
  refs TEXT
);

CREATE INDEX IF NOT EXISTS idx_memory_scope_kind ON memory_items(scope, kind);
CREATE INDEX IF NOT EXISTS idx_memory_key ON memory_items(key);
CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory_items(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_trace ON memory_items(trace_id);

CREATE TABLE IF NOT EXISTS world_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  state_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  trace_id TEXT NOT NULL
);

INSERT OR IGNORE INTO world_state (id, state_json, updated_at, trace_id)
VALUES (1, '{}', datetime('now'), 'bootstrap');
