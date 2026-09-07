SELECT
  region_id,
  fuel_type,
  MEASURE(average_actual_generation_mw) AS average_actual_generation_mw,
  MEASURE(estimated_actual_energy_mwh) AS estimated_actual_energy_mwh,
  MEASURE(partially_enriched_observation_count) AS partially_enriched_observation_count
FROM {{catalog}}.{{schema}}.nem_scada_generation_metrics
WHERE interval_end >= TIMESTAMPADD(HOUR, -24, (SELECT MAX(interval_end) FROM {{catalog}}.{{schema}}.nem_scada_generation_metrics))
GROUP BY ALL
ORDER BY estimated_actual_energy_mwh DESC;
