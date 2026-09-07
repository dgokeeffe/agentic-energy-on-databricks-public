SELECT
  region_id,
  MEASURE(average_dispatch_price_aud_per_mwh) AS average_dispatch_price_aud_per_mwh,
  MEASURE(maximum_dispatch_price_aud_per_mwh) AS maximum_dispatch_price_aud_per_mwh,
  MEASURE(average_total_demand_mw) AS average_total_demand_mw,
  MAX(source_publication_at) AS newest_source_publication_at,
  MAX(gold_published_at) AS newest_gold_publication_at
FROM {{catalog}}.{{schema}}.nem_region_dispatch_metrics
WHERE interval_end >= TIMESTAMPADD(HOUR, -24, (SELECT MAX(interval_end) FROM {{catalog}}.{{schema}}.nem_region_dispatch_metrics))
GROUP BY ALL
ORDER BY average_dispatch_price_aud_per_mwh DESC;
