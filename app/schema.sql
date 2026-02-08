-- app/schema.sql

PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS world_state_current (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  state TEXT NOT NULL CHECK (state IN ('DISARMED','ARMED_IDLE','ARMED_ACTIVE','FROZEN','ENDED')),
  reason TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL DEFAULT 'system'
);

CREATE TABLE IF NOT EXISTS world_state_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_state TEXT NOT NULL CHECK (from_state IN ('DISARMED','ARMED_IDLE','ARMED_ACTIVE','FROZEN','ENDED')),
  to_state   TEXT NOT NULL CHECK (to_state   IN ('DISARMED','ARMED_IDLE','ARMED_ACTIVE','FROZEN','ENDED')),
  reason TEXT NOT NULL DEFAULT '',
  actor TEXT NOT NULL DEFAULT 'system',
  created_at TEXT NOT NULL,
  trace_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_world_state_events_created_at
  ON world_state_events(created_at);
