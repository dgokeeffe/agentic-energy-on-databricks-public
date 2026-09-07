SELECT
  interconnector_id,
  MEASURE(average_source_sign_flow_mw) AS average_source_sign_flow_mw,
  MEASURE(estimated_source_sign_flow_mwh) AS estimated_source_sign_flow_mwh,
  MEASURE(average_losses_mw) AS average_losses_mw
FROM {{catalog}}.{{schema}}.nem_interconnector_flow_metrics
WHERE interval_end >= TIMESTAMPADD(HOUR, -24, (SELECT MAX(interval_end) FROM {{catalog}}.{{schema}}.nem_interconnector_flow_metrics))
GROUP BY ALL
ORDER BY interconnector_id;
