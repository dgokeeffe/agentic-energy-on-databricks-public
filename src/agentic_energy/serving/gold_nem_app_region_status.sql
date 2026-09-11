-- Lakehouse-owned regular Delta source. Preserve history and update corrections by key.
CREATE TABLE IF NOT EXISTS IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_app_region_status')
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true', 'delta.enableRowTracking' = 'true')
AS SELECT *, CAST(:source_mode AS STRING) AS source_mode FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_app_region_status') WHERE FALSE;

ALTER TABLE IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_app_region_status') SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

SELECT assert_true(COUNT(*) > 0, 'Publication requires a nonempty source') FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_app_region_status');
SELECT assert_true(COUNT(*) = 0, 'Publication requires unique nonnull keys') FROM (
  SELECT serving_key FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_app_region_status')
  GROUP BY serving_key HAVING COUNT(*) > 1 OR serving_key IS NULL
);

MERGE WITH SCHEMA EVOLUTION INTO IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_app_region_status') AS target
USING (SELECT *, CAST(:source_mode AS STRING) AS source_mode FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_app_region_status')) AS source
ON target.serving_key = source.serving_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
