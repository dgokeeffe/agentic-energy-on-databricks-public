-- Publish a regular Delta synced-table source from the pipeline-owned materialized view.
-- The lakehouse job is the only writer. Rows remain labelled snapshot/prepared through source metadata.
CREATE TABLE IF NOT EXISTS IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_app_region_status')
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.enableRowTracking' = 'true',
  'quality' = 'gold',
  'data.classification' = 'mode_explicit'
)
AS
SELECT *, CAST(:source_mode AS STRING) AS source_mode
FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_app_region_status')
WHERE FALSE;

SELECT assert_true(
  COUNT(*) > 0,
  'app serving publication refused an empty pipeline-owned source'
)
FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_app_region_status');

SELECT assert_true(
  (SELECT COUNT(*) FROM IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_app_region_status')) = 0
  OR 2 * (
    SELECT COUNT(*)
    FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_app_region_status') AS source
    INNER JOIN IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_app_region_status') AS target
      ON source.serving_key = target.serving_key
  ) >= (SELECT COUNT(*) FROM IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_app_region_status')),
  'app serving publication refused to remove more than half of existing rows'
);

MERGE INTO IDENTIFIER(:catalog || '.' || :app_serving_schema || '.gold_nem_app_region_status') AS target
USING (
  SELECT *, CAST(:source_mode AS STRING) AS source_mode
  FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_nem_app_region_status')
) AS source
ON target.serving_key = source.serving_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
WHEN NOT MATCHED BY SOURCE THEN DELETE;
