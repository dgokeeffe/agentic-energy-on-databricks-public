WITH fuel AS (
  SELECT f.interval_end, f.region_id,
         SUM(f.actual_generation_mw) AS mw,
         SUM(f.facility_count) AS units,
         SUM(f.partially_enriched_facility_count) AS partial,
         MAX(f.source_publication_at) AS published
  FROM ${catalog}.${schema}.gold_nem_scada_generation_5min f
  GROUP BY f.interval_end, f.region_id
), supply AS (
  SELECT s.* FROM ${catalog}.${schema}.gold_nem_initial_supply_5min s
), mismatches AS (
  SELECT f.interval_end
  FROM fuel f FULL OUTER JOIN supply s
    ON f.interval_end = s.interval_end AND f.region_id = s.region_id
  WHERE f.interval_end IS NULL OR s.interval_end IS NULL
     OR s.actual_supply_mw IS NULL OR ABS(f.mw - s.actual_supply_mw) > 0.000001
     OR NOT (f.units <=> s.observed_unit_count)
     OR NOT (f.partial <=> s.partially_enriched_unit_count)
     OR NOT (f.published <=> s.source_publication_at)
), duplicate_keys AS (
  SELECT s.interval_end, s.region_id FROM supply s
  GROUP BY s.interval_end, s.region_id HAVING COUNT(*) <> 1
), effective AS (
  SELECT r.interval_end, r.region_id
  FROM ${catalog}.${schema}.gold_nem_region_dispatch_5min r
  GROUP BY r.interval_end, r.region_id
  HAVING SUM(CASE WHEN r.is_effective_run THEN 1 ELSE 0 END) <> 1
)
SELECT 'supply_reconciles_to_independent_fuel_product' AS check_name, COUNT(*) AS violations FROM mismatches
UNION ALL SELECT 'supply_key_uniqueness', COUNT(*) FROM duplicate_keys
UNION ALL SELECT 'nonnull_key_and_processing_time', COUNT(*) FROM supply s
  WHERE s.interval_end IS NULL OR s.region_id IS NULL OR s.gold_published_at IS NULL
UNION ALL SELECT 'nonempty_snapshot', CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END FROM supply
UNION ALL SELECT 'effective_intervention_uniqueness', COUNT(*) FROM effective
UNION ALL SELECT 'signed_charging_fixture_present', CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
  FROM ${catalog}.${schema}.gold_nem_unit_dispatch_5min u WHERE u.actual_generation_mw < 0
