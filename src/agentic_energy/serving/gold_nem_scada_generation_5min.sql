-- Lakehouse-owned regular Delta source. Preserve history and update corrections by key.
CREATE TABLE IF NOT EXISTS IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min')
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true', 'delta.enableRowTracking' = 'true')
AS SELECT *, CAST(:source_mode AS STRING) AS source_mode FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min') WHERE FALSE;

ALTER TABLE IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min') SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

SELECT assert_true(COUNT(*) > 0, 'Publication requires a nonempty source') FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min');
SELECT assert_true(COUNT(*) = 0, 'Publication requires unique nonnull keys') FROM (
  SELECT interval_end, region_id, fuel_type FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min')
  GROUP BY interval_end, region_id, fuel_type HAVING COUNT(*) > 1 OR interval_end IS NULL OR region_id IS NULL OR fuel_type IS NULL
);

MERGE WITH SCHEMA EVOLUTION INTO IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_scada_generation_5min') AS target
USING (SELECT *, CAST(:source_mode AS STRING) AS source_mode FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_scada_generation_5min')) AS source
ON target.interval_end = source.interval_end AND target.region_id = source.region_id AND target.fuel_type = source.fuel_type
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
