/** Fixed Lakebase reads. Identifiers and bounds are never caller controlled. */
export const servingQueries = {
  '/api/region-status': `SELECT source_mode, region_id, interval_end, intervention,
    rrp_aud_per_mwh, total_demand_mw, price_source_run_no, demand_source_run_no,
    source_interval_watermark, source_publication_at, gold_published_at,
    market_wide_binding_constraint_count, market_wide_interconnector_count,
    market_wide_interconnector_source_sign_flow_mw
    FROM app_read.nem_region_status_synced
    ORDER BY interval_end DESC, region_id LIMIT 100`,
  '/api/fuel-generation': `SELECT interval_end, region_id, fuel_type,
    actual_generation_mw, facility_count, partially_enriched_facility_count,
    registration_publication_at, registration_coverage_seconds, registration_coverage_basis
    FROM app_read.nem_fuel_generation_synced
    ORDER BY interval_end DESC, region_id, fuel_type LIMIT 1000`,
  '/api/unit-dispatch': `SELECT interval_end, duid, actual_generation_mw,
    region_id, fuel_type, registered_capacity_mw, dimension_match_status
    FROM app_read.nem_unit_dispatch_synced
    ORDER BY interval_end DESC, duid LIMIT 1800`,
} as const;
