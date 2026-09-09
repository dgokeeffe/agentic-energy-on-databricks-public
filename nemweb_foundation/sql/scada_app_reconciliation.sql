-- Read-only reconciliation for the two SCADA Gold contracts consumed by the app.
-- UNKNOWN enrichment is valid and counted. Missing or duplicated DUIDs and
-- mismatched signed MW fail closed. SCADA carries no intervention dimension.
USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

SELECT assert_true(
  COUNT_IF(s.duid IS NULL OR u.duid IS NULL) = 0,
  'SCADA DUID coverage does not reconcile between Silver and unit Gold'
)
FROM silver_nem_dispatch_unit_scada s
FULL OUTER JOIN gold_nem_unit_dispatch_5min u
  ON s.interval_end = u.interval_end AND s.duid = u.duid;

SELECT assert_true(COUNT(*) = 0, 'SCADA signed MW does not reconcile between unit and fuel Gold')
FROM (
  SELECT COALESCE(u.interval_end, g.interval_end) AS interval_end
  FROM (
    SELECT interval_end, SUM(actual_generation_mw) AS unit_mw
    FROM gold_nem_unit_dispatch_5min
    GROUP BY interval_end
  ) u
  FULL OUTER JOIN (
    SELECT interval_end, SUM(actual_generation_mw) AS generation_mw
    FROM gold_nem_scada_generation_5min
    GROUP BY interval_end
  ) g USING (interval_end)
  WHERE u.unit_mw IS NULL OR g.generation_mw IS NULL
     OR ABS(u.unit_mw - g.generation_mw) > 0.000001
);

SELECT assert_true(COUNT(*) = 0, 'SCADA partial-enrichment counts do not reconcile')
FROM (
  SELECT
    COALESCE(u.interval_end, g.interval_end) AS interval_end,
    COALESCE(u.region_id, g.region_id) AS region_id,
    COALESCE(u.fuel_type, g.fuel_type) AS fuel_type
  FROM (
    SELECT interval_end, region_id, fuel_type,
           COUNT_IF(dimension_match_status <> 'REGION_AND_FUEL') AS partial_units
    FROM gold_nem_unit_dispatch_5min
    GROUP BY interval_end, region_id, fuel_type
  ) u
  FULL OUTER JOIN (
    SELECT interval_end, region_id, fuel_type,
           partially_enriched_facility_count AS partial_units
    FROM gold_nem_scada_generation_5min
  ) g USING (interval_end, region_id, fuel_type)
  WHERE u.partial_units IS NULL OR g.partial_units IS NULL
     OR u.partial_units <> g.partial_units
);

-- One compact coverage row for operator evidence at the newest represented
-- interval. Ratios are observations, not pass thresholds; unmatched virtual or
-- newly registered DUIDs stay visible instead of being silently discarded.
WITH latest AS (
  SELECT MAX(interval_end) AS interval_end
  FROM gold_nem_unit_dispatch_5min
)
SELECT
  latest.interval_end,
  COUNT(*) AS unit_row_count,
  COUNT(DISTINCT duid) AS distinct_duid_count,
  COUNT_IF(dimension_match_status = 'REGION_AND_FUEL') AS fully_enriched_duid_count,
  COUNT_IF(dimension_match_status = 'REGION_ONLY') AS region_only_duid_count,
  COUNT_IF(dimension_match_status = 'FUEL_ONLY') AS fuel_only_duid_count,
  COUNT_IF(dimension_match_status = 'UNMATCHED') AS unmatched_duid_count,
  SUM(actual_generation_mw) AS signed_unit_generation_mw,
  MAX(source_publication_at) AS newest_source_publication_at,
  MAX(gold_published_at) AS newest_gold_published_at
FROM gold_nem_unit_dispatch_5min
CROSS JOIN latest
WHERE gold_nem_unit_dispatch_5min.interval_end = latest.interval_end
GROUP BY latest.interval_end;
