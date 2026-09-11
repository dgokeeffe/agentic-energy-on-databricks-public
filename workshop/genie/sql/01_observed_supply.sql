SELECT s.interval_end, s.region_id, s.actual_supply_mw,
       s.observed_unit_count, s.partially_enriched_unit_count,
       s.source_publication_at, s.gold_published_at
FROM ${catalog}.${schema}.gold_nem_initial_supply_5min s
WHERE s.interval_end >= TIMESTAMP '2026-07-01 00:05:00+10:00'
  AND s.interval_end <= TIMESTAMP '2026-07-01 00:10:00+10:00'
ORDER BY s.interval_end, s.region_id LIMIT 100
