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
CREATE TABLE IF NOT EXISTS IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min')
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.enableRowTracking' = 'true',
  'quality' = 'gold',
  'grain' = 'five_minutes',
  'source.timezone' = 'AEST',
  'availability' = 'not_published_in_current',
  'data.classification' = 'prepared_non_live'
)
AS
SELECT *
FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min')
WHERE FALSE;

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
USING IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min') AS source
ON target.interval_end = source.interval_end
   AND target.region_id = source.region_id
   AND target.fuel_type = source.fuel_type
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
WHEN NOT MATCHED BY SOURCE THEN DELETE;
