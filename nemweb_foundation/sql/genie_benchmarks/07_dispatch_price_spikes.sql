SELECT
  region_id,
  price_formation_basis,
  MEASURE(spike_interval_count) AS spike_interval_count,
  MEASURE(decided_interval_count) AS decided_interval_count,
  MEASURE(five_minute_interval_count) AS five_minute_interval_count,
  MEASURE(maximum_dispatch_price_aud_per_mwh) AS maximum_dispatch_price_aud_per_mwh,
  MAX(gold_published_at) AS newest_gold_publication_at
FROM {{catalog}}.{{schema}}.nem_dispatch_price_spike_metrics
WHERE interval_end >= TIMESTAMPADD(HOUR, -24, (SELECT MAX(interval_end) FROM {{catalog}}.{{schema}}.nem_dispatch_price_spike_metrics))
GROUP BY ALL
ORDER BY spike_interval_count DESC, region_id
