-- AppKit Analytics read path over the run-specific regular Delta serving table.
-- Keeping the identifier in reviewed SQL prevents callers from selecting another object.
SELECT
  region_id,
  interval_end,
  intervention,
  rrp_aud_per_mwh,
  total_demand_mw,
  price_source_run_no,
  demand_source_run_no,
  source_interval_watermark,
  source_publication_at,
  gold_published_at,
  market_wide_binding_constraint_count,
  market_wide_interconnector_count,
  market_wide_interconnector_source_sign_flow_mw,
  prediction_score,
  prediction_model_version,
  prediction_feature_time,
  prediction_scored_at,
  prediction_source_freshness,
  prediction_missing_feature_status
FROM edp_entdata_exp_dev_landing.agentic_energy_workshop_d4_serving.gold_nem_app_region_status
WHERE is_effective_run = TRUE
ORDER BY interval_end DESC, region_id
LIMIT 100
