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
