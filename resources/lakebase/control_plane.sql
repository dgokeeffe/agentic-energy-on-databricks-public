CREATE SCHEMA IF NOT EXISTS agentic_energy;

CREATE TABLE IF NOT EXISTS agentic_energy.source_metadata (
    source_id TEXT PRIMARY KEY,
    source_version TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    provider TEXT NOT NULL,
    dataset TEXT NOT NULL,
    region TEXT NOT NULL,
    url_or_fixture_path TEXT NOT NULL,
    extraction_mode TEXT NOT NULL CHECK (extraction_mode IN ('fixture', 'live')),
    file_name_regex TEXT,
    format TEXT NOT NULL,
    compression TEXT NOT NULL,
    parser_key TEXT NOT NULL,
    schema_reference TEXT NOT NULL,
    source_timezone TEXT NOT NULL,
    event_timestamp_field TEXT NOT NULL,
    ingestion_timestamp_field TEXT NOT NULL,
    natural_key JSONB NOT NULL,
    watermark_field TEXT NOT NULL,
    deduplication_rule TEXT NOT NULL,
    quality_checks JSONB NOT NULL,
    quarantine_policy TEXT NOT NULL,
    schedule TEXT NOT NULL,
    serverless_worker_key TEXT NOT NULL,
    landing_volume_path TEXT NOT NULL,
    target_catalog TEXT,
    target_schema TEXT,
    licensing_provenance TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by TEXT NOT NULL DEFAULT current_user
);

CREATE TABLE IF NOT EXISTS agentic_energy.metadata_versions (
    snapshot_id TEXT PRIMARY KEY,
    source_ids JSONB NOT NULL,
    metadata_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by TEXT NOT NULL DEFAULT current_user,
    status TEXT NOT NULL CHECK (status IN ('validated', 'superseded', 'rejected'))
);

CREATE TABLE IF NOT EXISTS agentic_energy.pipeline_runs (
    run_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES agentic_energy.metadata_versions(snapshot_id),
    mode TEXT NOT NULL CHECK (mode IN ('fixture', 'live')),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('planned', 'running', 'succeeded', 'failed', 'cancelled')),
    bronze_count BIGINT,
    accepted_count BIGINT,
    quarantine_count BIGINT,
    silver_count BIGINT,
    gold_count BIGINT,
    watermark TEXT,
    freshness TIMESTAMPTZ,
    failure_stage TEXT,
    failure_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agentic_energy.pipeline_run_sources (
    run_id TEXT NOT NULL REFERENCES agentic_energy.pipeline_runs(run_id),
    source_id TEXT NOT NULL REFERENCES agentic_energy.source_metadata(source_id),
    worker_run_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('planned', 'running', 'succeeded', 'failed', 'skipped')),
    bronze_count BIGINT,
    accepted_count BIGINT,
    quarantine_count BIGINT,
    silver_count BIGINT,
    watermark TEXT,
    freshness TIMESTAMPTZ,
    failure_stage TEXT,
    failure_code TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    PRIMARY KEY (run_id, source_id)
);

-- Native, application-owned annotation table (challenge-spec 8.2).
--
-- Writable Postgres state sitting alongside the read-only synced Gold relation.
-- Authorship is assigned by the database, never by the caller: an
-- author_identity the client can set is not an identity but free text, and the
-- audit trail would then faithfully record a forged author.
CREATE TABLE IF NOT EXISTS agentic_energy.operator_annotations (
    annotation_id BIGSERIAL PRIMARY KEY,
    gold_entity_key TEXT NOT NULL CHECK (gold_entity_key ~ '^[A-Z0-9]+\|[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'),
    note TEXT NOT NULL CHECK (btrim(note) <> ''),
    status TEXT NOT NULL DEFAULT 'flagged' CHECK (status IN ('reviewed', 'flagged', 'acknowledged')),
    author_identity TEXT NOT NULL DEFAULT current_user,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    audit_version INT NOT NULL DEFAULT 1 CHECK (audit_version >= 1)
);

CREATE INDEX IF NOT EXISTS operator_annotations_entity_idx
    ON agentic_energy.operator_annotations (gold_entity_key, updated_at DESC);
CREATE INDEX IF NOT EXISTS operator_annotations_author_idx
    ON agentic_energy.operator_annotations (author_identity, updated_at DESC);

-- Audit fields are maintained server-side. Without this the columns are
-- stale-by-construction: updated_at would keep its insert value forever and
-- audit_version would never leave 1, which is worse than having no audit
-- fields because the row still looks authoritative. The trigger touches only
-- this table, so it is not a write-back path into Gold (spec 8.3).
CREATE OR REPLACE FUNCTION agentic_energy.operator_annotations_touch()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    NEW.audit_version := OLD.audit_version + 1;
    -- Authorship and creation time are immutable once written.
    NEW.author_identity := OLD.author_identity;
    NEW.created_at := OLD.created_at;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS operator_annotations_touch_trg ON agentic_energy.operator_annotations;
CREATE TRIGGER operator_annotations_touch_trg
    BEFORE UPDATE ON agentic_energy.operator_annotations
    FOR EACH ROW EXECUTE FUNCTION agentic_energy.operator_annotations_touch();

-- Role separation (spec 8.4). Roles are cluster-level and have no
-- IF NOT EXISTS, so guard them for repeat applies.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agentic_energy_annotator') THEN
        CREATE ROLE agentic_energy_annotator NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agentic_energy_reader') THEN
        CREATE ROLE agentic_energy_reader NOLOGIN;
    END IF;
END
$$;

-- Row-level security is what actually separates authors. The grants below are
-- table-wide; without RLS any annotator could rewrite any other author's row.
ALTER TABLE agentic_energy.operator_annotations ENABLE ROW LEVEL SECURITY;
-- FORCE so the table owner is held to the same boundary rather than bypassing it.
ALTER TABLE agentic_energy.operator_annotations FORCE ROW LEVEL SECURITY;

-- Annotations and their audit context are readable by the whole workspace
-- (spec 8.3 step 3); only writes are identity-scoped.
DROP POLICY IF EXISTS operator_annotations_select ON agentic_energy.operator_annotations;
CREATE POLICY operator_annotations_select
    ON agentic_energy.operator_annotations
    FOR SELECT
    USING (true);

-- New rows are bound to the session identity, so a caller cannot file a note
-- under another principal.
DROP POLICY IF EXISTS operator_annotations_insert ON agentic_energy.operator_annotations;
CREATE POLICY operator_annotations_insert
    ON agentic_energy.operator_annotations
    FOR INSERT
    WITH CHECK (author_identity = current_user);

-- USING decides which rows may be modified; WITH CHECK decides what they may
-- become. USING alone would let an author hand a row to another identity and
-- escape their own audit trail.
DROP POLICY IF EXISTS operator_annotations_update ON agentic_energy.operator_annotations;
CREATE POLICY operator_annotations_update
    ON agentic_energy.operator_annotations
    FOR UPDATE
    USING (author_identity = current_user)
    WITH CHECK (author_identity = current_user);

GRANT USAGE ON SCHEMA agentic_energy TO agentic_energy_annotator, agentic_energy_reader;
-- INSERT/UPDATE only. No DELETE: annotations are audit records, superseded by
-- status changes rather than destroyed.
GRANT SELECT, INSERT, UPDATE ON agentic_energy.operator_annotations TO agentic_energy_annotator;
GRANT USAGE, SELECT ON SEQUENCE agentic_energy.operator_annotations_annotation_id_seq TO agentic_energy_annotator;
GRANT SELECT ON agentic_energy.operator_annotations TO agentic_energy_reader;

CREATE INDEX IF NOT EXISTS pipeline_runs_status_idx
    ON agentic_energy.pipeline_runs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS pipeline_run_sources_source_idx
    ON agentic_energy.pipeline_run_sources (source_id, completed_at DESC);

INSERT INTO agentic_energy.source_metadata (
    source_id, source_version, active, provider, dataset, region,
    url_or_fixture_path, extraction_mode, file_name_regex, format, compression,
    parser_key, schema_reference, source_timezone, event_timestamp_field,
    ingestion_timestamp_field, natural_key, watermark_field,
    deduplication_rule, quality_checks, quarantine_policy, schedule,
    serverless_worker_key, landing_volume_path, target_catalog, target_schema,
    licensing_provenance
) VALUES
(
    'aemo_dispatchis_live', '1.0', TRUE, 'AEMO', 'DISPATCHIS', 'NEM',
    'https://nemweb.com.au/Reports/Current/DispatchIS_Reports/', 'live',
    'PUBLIC_DISPATCHIS_.*\\.zip$', 'ZIP_CSV', 'zip',
    'aemo_dispatchis_v1', 'aemo_dispatchis_price_regionsum_v1', 'Australia/Brisbane',
    'interval_datetime', '_ingested_at', '["region", "interval_datetime"]',
    'interval_datetime', 'last_by_ingestion_sequence',
    '["demand_mw >= 0", "price_per_mwh is not null"]', 'isolate_with_reason',
    '*/5 * * * *', 'generic_source_worker',
    '/Volumes/<catalog>/<schema>/agentic_energy/landing', NULL, NULL,
    'AEMO NEMWEB public DISPATCHIS report; verify workshop use terms before deployment'
),
(
    'weather_fixture', '1.0', TRUE, 'Open-Meteo', 'HOURLY_WEATHER', 'NEM',
    'fixtures/weather.jsonl', 'fixture', NULL, 'JSONL', 'none',
    'jsonl_fixture_v1', 'weather_fixture_v1', 'Australia/Sydney',
    'observed_at', '_ingested_at', '["region", "observed_at"]',
    'observed_at', 'last_by_ingestion_sequence',
    '["temperature_c is not null", "region is not null"]', 'isolate_with_reason',
    'manual', 'generic_source_worker',
    '/Volumes/<catalog>/<schema>/agentic_energy/landing', NULL, NULL,
    'Open-Meteo-shaped deterministic workshop fixture'
)
ON CONFLICT (source_id) DO UPDATE SET
    source_version = EXCLUDED.source_version,
    active = EXCLUDED.active,
    provider = EXCLUDED.provider,
    dataset = EXCLUDED.dataset,
    region = EXCLUDED.region,
    url_or_fixture_path = EXCLUDED.url_or_fixture_path,
    extraction_mode = EXCLUDED.extraction_mode,
    file_name_regex = EXCLUDED.file_name_regex,
    format = EXCLUDED.format,
    compression = EXCLUDED.compression,
    parser_key = EXCLUDED.parser_key,
    schema_reference = EXCLUDED.schema_reference,
    source_timezone = EXCLUDED.source_timezone,
    event_timestamp_field = EXCLUDED.event_timestamp_field,
    ingestion_timestamp_field = EXCLUDED.ingestion_timestamp_field,
    natural_key = EXCLUDED.natural_key,
    watermark_field = EXCLUDED.watermark_field,
    deduplication_rule = EXCLUDED.deduplication_rule,
    quality_checks = EXCLUDED.quality_checks,
    quarantine_policy = EXCLUDED.quarantine_policy,
    schedule = EXCLUDED.schedule,
    serverless_worker_key = EXCLUDED.serverless_worker_key,
    landing_volume_path = EXCLUDED.landing_volume_path,
    licensing_provenance = EXCLUDED.licensing_provenance,
    updated_at = now(),
    updated_by = current_user;

INSERT INTO agentic_energy.metadata_versions (snapshot_id, source_ids, metadata_payload, status)
SELECT
    'seed-20260810-113532',
    jsonb_agg(source_id ORDER BY source_id),
    jsonb_agg(to_jsonb(source_metadata) ORDER BY source_id),
    'validated'
FROM agentic_energy.source_metadata
ON CONFLICT (snapshot_id) DO NOTHING;

COMMENT ON TABLE agentic_energy.source_metadata IS
    'Persistent control-plane metadata. Rows select registered adapters; they do not contain executable code.';
COMMENT ON TABLE agentic_energy.metadata_versions IS
    'Immutable metadata snapshots used to make each ingestion run reproducible.';
COMMENT ON TABLE agentic_energy.pipeline_runs IS
    'One row per dispatcher run across the selected source set.';
COMMENT ON TABLE agentic_energy.pipeline_run_sources IS
    'Per-source worker execution and reconciliation evidence.';
COMMENT ON TABLE agentic_energy.operator_annotations IS
    'Native writable operator annotations. Authorship is server-assigned from '
    'current_user and enforced by row-level security; annotations never mutate '
    'Gold and never flow back to the upstream provider.';
COMMENT ON COLUMN agentic_energy.operator_annotations.gold_entity_key IS
    'Logical Gold business key (region|interval_utc). Validated by CHECK rather '
    'than a physical foreign key, because a synced read-only relation may not '
    'support inbound FK enforcement (spec 8.2).';
