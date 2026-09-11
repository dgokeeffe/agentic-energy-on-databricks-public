-- Lakehouse-owned regular Delta source. Preserve history and update corrections by key.
CREATE TABLE IF NOT EXISTS IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_unit_dispatch_5min')
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true', 'delta.enableRowTracking' = 'true')
AS SELECT *, CAST(:source_mode AS STRING) AS source_mode FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_unit_dispatch_5min') WHERE FALSE;

ALTER TABLE IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_unit_dispatch_5min') SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

SELECT assert_true(COUNT(*) > 0, 'Publication requires a nonempty source') FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_unit_dispatch_5min');
SELECT assert_true(COUNT(*) = 0, 'Publication requires unique nonnull keys') FROM (
  SELECT interval_end, duid FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_unit_dispatch_5min')
  GROUP BY interval_end, duid HAVING COUNT(*) > 1 OR interval_end IS NULL OR duid IS NULL
);

MERGE WITH SCHEMA EVOLUTION INTO IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_unit_dispatch_5min') AS target
USING (SELECT *, CAST(:source_mode AS STRING) AS source_mode FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_unit_dispatch_5min')) AS source
ON target.interval_end = source.interval_end AND target.duid = source.duid
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
