SELECT r.interval_end, r.region_id, r.rrp_aud_per_mwh,
       r.total_demand_mw, r.intervention, r.price_source_run_no,
       r.demand_source_run_no, r.source_publication_at
FROM ${catalog}.${schema}.gold_nem_region_dispatch_5min r
WHERE r.is_effective_run
  AND r.interval_end >= TIMESTAMP '2026-07-01 00:05:00+10:00'
  AND r.interval_end <= TIMESTAMP '2026-07-01 00:10:00+10:00'
ORDER BY r.interval_end, r.region_id LIMIT 100
