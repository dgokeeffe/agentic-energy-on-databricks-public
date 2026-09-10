-- Alert-ready regional dispatch-price spike summary for the last 24 hours.
-- Every row carries the threshold that fired and its freshness, so an operator can
-- see whether the result is current enough to act on. Zero spiking intervals is a
-- valid answer and is distinguishable from absent data by the interval count.
SELECT
  region_id,
  MEASURE(price_spike_interval_count) AS price_spike_interval_count,
  MEASURE(five_minute_interval_count) AS five_minute_interval_count,
  MEASURE(maximum_spike_price_aud_per_mwh) AS maximum_spike_price_aud_per_mwh,
  MEASURE(stale_price_spike_interval_count) AS stale_price_spike_interval_count,
  MAX(spike_threshold_aud_per_mwh) AS spike_threshold_aud_per_mwh,
  MAX(source_publication_at) AS newest_source_publication_at,
  MAX(gold_published_at) AS newest_gold_publication_at
FROM {{catalog}}.{{schema}}.nem_dispatch_price_spike_metrics
WHERE interval_end >= TIMESTAMPADD(HOUR, -24, (SELECT MAX(interval_end) FROM {{catalog}}.{{schema}}.nem_dispatch_price_spike_metrics))
GROUP BY ALL
ORDER BY price_spike_interval_count DESC, region_id
