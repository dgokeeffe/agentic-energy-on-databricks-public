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

-- Evolve a serving table that was created before the attribution columns existed.
--
-- CREATE TABLE IF NOT EXISTS above is a no-op against a deployed table, so it adds
-- nothing; and the MERGE below uses UPDATE SET * / INSERT *, which requires the
-- two schemas to agree. There is no autoMerge setting anywhere in this repository,
-- and enabling one here would let any future pipeline column arrive in the serving
-- surface unreviewed. So the columns are named explicitly instead.
--
-- IF NOT EXISTS makes this idempotent, which matters because the publication job
-- runs on every refresh, not only at deploy time.
ALTER TABLE IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min')
ADD COLUMNS IF NOT EXISTS (
  registration_effective_at TIMESTAMP COMMENT 'Fixed-AEST market instant the registration dimension was evaluated at: the maximum SCADA interval present in Bronze. Never difference this against a UTC publication timestamp.',
  registration_publication_at TIMESTAMP COMMENT 'UTC publication instant of the weakest of the three monthly registration loads.',
  registration_coverage_seconds BIGINT COMMENT 'Signed UTC publication-time distance from the dispatch data being priced to the registration context attributing it. NULL means not assessable, never zero.',
  registration_coverage_basis STRING COMMENT 'LISTING_OR_HTTP when the publication instants are vouchable; DEGRADED_RETRIEVAL_FALLBACK when one was derived from our own retrieval and the coverage figure therefore proves nothing; UNKNOWN when absent.'
);

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

MERGE INTO IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min') AS target
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
