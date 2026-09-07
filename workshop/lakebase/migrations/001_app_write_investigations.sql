-- Canonical idempotent native Lakebase migration. The app service identity owns app_write.
CREATE SCHEMA IF NOT EXISTS app_write;

CREATE TABLE IF NOT EXISTS app_write.investigations (
  investigation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nem_event_key TEXT NOT NULL,
  region_id TEXT NOT NULL,
  interval_end TIMESTAMPTZ NOT NULL,
  operator_identity TEXT NOT NULL,
  team_identifier TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open', 'reviewing', 'closed')),
  decision TEXT NOT NULL DEFAULT '',
  evidence_reference TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  version BIGINT NOT NULL DEFAULT 1 CHECK (version > 0)
);

ALTER TABLE app_write.investigations REPLICA IDENTITY FULL;
