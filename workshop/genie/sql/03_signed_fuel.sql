SELECT f.interval_end, f.region_id, f.fuel_type,
       f.actual_generation_mw, f.facility_count,
       f.partially_enriched_facility_count, f.registration_coverage_seconds,
       f.registration_coverage_basis
FROM ${catalog}.${schema}.gold_nem_scada_generation_5min f
WHERE f.interval_end >= TIMESTAMP '2026-07-01 00:05:00+10:00'
  AND f.interval_end <= TIMESTAMP '2026-07-01 00:10:00+10:00'
ORDER BY f.interval_end, f.region_id, f.fuel_type LIMIT 100
