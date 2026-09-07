SELECT
  region_id,
  fuel_type,
  MEASURE(average_dispatch_target_mw) AS average_dispatch_target_mw,
  MEASURE(average_availability_mw) AS average_availability_mw,
  MEASURE(mean_absolute_scada_target_variance_mw) AS mean_absolute_scada_target_variance_mw,
  MAX(source_publication_at) AS newest_t1_source_publication_at
FROM {{catalog}}.{{schema}}.nem_unit_availability_t1_metrics
WHERE interval_end >= TIMESTAMPADD(DAY, -7, (SELECT MAX(interval_end) FROM {{catalog}}.{{schema}}.nem_unit_availability_t1_metrics))
GROUP BY ALL
ORDER BY average_availability_mw DESC;
