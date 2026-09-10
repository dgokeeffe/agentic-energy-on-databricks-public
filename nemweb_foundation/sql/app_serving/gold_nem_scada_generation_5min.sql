-- Publish a regular Delta serving source for five-minute generation by region and fuel.
-- The lakehouse job is the only writer. Rows remain labelled snapshot/prepared through source metadata.
--
-- This is the second app serving surface, added for the Track C value-capture screen.
-- It is published separately from gold_nem_app_region_status, and granted separately
-- in the app bundle, so the application's privileges stay enumerable.
--
-- Grain is (interval_end, region_id, fuel_type). actual_generation_mw is a signed
-- sum, so a charging battery is negative and must never be treated as generation.
-- This is actual SCADA output only: AEMO Current publishes no five-minute
-- availability, so nothing here supports an availability or curtailment claim.
--
-- Two clocks, never to be differenced. interval_end and registration_effective_at
-- are interval-ending fixed AEST (UTC+10, no daylight saving). Every publication,
-- landing and processing timestamp — including registration_publication_at and the
-- registration_coverage_seconds delta computed from it — is UTC. Subtracting one
-- domain from the other yields a result ten hours wrong.
--
-- registration_coverage_seconds is signed and may be NULL. Negative means the
-- registration load was published after the dispatch data it describes, which is
-- ordinary for a monthly source. NULL means the distance could not be established
-- and must be read as "not assessable", never as zero; a consumer defaulting it to
-- zero would report the strongest possible freshness from the weakest possible
-- evidence. registration_coverage_basis carries which of those applies.
CREATE TABLE IF NOT EXISTS IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min')
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.enableRowTracking' = 'true',
  'quality' = 'gold',
  'grain' = 'five_minutes',
  'source.timezone' = 'AEST',
  'availability' = 'not_published_in_current',
  'registration.coverage' = 'utc_publication_delta',
  'data.classification' = 'mode_explicit'
)
AS
SELECT *, CAST(:source_mode AS STRING) AS source_mode
FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min')
WHERE FALSE;

-- Schema evolution is handled on the MERGE itself, at the bottom of this file.
--
-- CREATE TABLE IF NOT EXISTS above is a no-op against an already-deployed table, so
-- it cannot add the attribution columns; and the MERGE uses UPDATE SET * / INSERT *,
-- which requires both schemas to agree. Something has to reconcile them.
--
-- An earlier version of this file used ALTER TABLE ... ADD COLUMNS IF NOT EXISTS.
-- That is NOT valid Databricks SQL: the engine returns PARSE_SYNTAX_ERROR at
-- 'EXISTS' (SQLSTATE 42601), because ADD COLUMNS has no IF NOT EXISTS clause. It
-- would have failed this task on the next refresh, and no local test can catch it
-- because none of them reach a SQL engine. Plain ADD COLUMNS is valid but is not
-- idempotent — it errors once the column exists — and this job runs on every
-- refresh rather than only at deploy, so a bare ALTER is also wrong here.
--
-- MERGE WITH SCHEMA EVOLUTION is per-statement and reviewed: it evolves the target
-- to match this one source and nothing else. That is deliberately narrower than the
-- spark.databricks.delta.schema.autoMerge.enabled table property, which would let
-- any future pipeline column reach the serving surface unreviewed and is used
-- nowhere in this repository.

SELECT assert_true(
  COUNT(*) > 0,
  'app serving publication refused an empty pipeline-owned generation source'
)
FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min');

-- Refuse a publication that would remove more than half of the existing rows.
-- The natural key is the composite (interval_end, region_id, fuel_type); unlike the
-- region-status table there is no single serving_key column, so the overlap is
-- counted on all three fields.
SELECT assert_true(
  (SELECT COUNT(*) FROM IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min')) = 0
  OR 2 * (
    SELECT COUNT(*)
    FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min') AS source
    INNER JOIN IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min') AS target
      ON source.interval_end = target.interval_end
     AND source.region_id = target.region_id
     AND source.fuel_type = target.fuel_type
  ) >= (SELECT COUNT(*) FROM IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min')),
  'app serving publication refused to remove more than half of existing generation rows'
);

MERGE WITH SCHEMA EVOLUTION
INTO IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min') AS target
USING (
  SELECT *, CAST(:source_mode AS STRING) AS source_mode
  FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min')
) AS source
ON target.interval_end = source.interval_end
   AND target.region_id = source.region_id
   AND target.fuel_type = source.fuel_type
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
WHEN NOT MATCHED BY SOURCE THEN DELETE;
