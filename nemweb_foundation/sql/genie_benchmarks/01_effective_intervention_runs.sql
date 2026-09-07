-- Returns rows only when effective intervention semantics are violated.
SELECT
  interval_end,
  region_id,
  COUNT(*) AS retained_intervention_rows,
  COUNT_IF(is_effective_run) AS effective_row_count,
  SORT_ARRAY(COLLECT_SET(intervention)) AS retained_intervention_flags
FROM {{catalog}}.{{schema}}.gold_nem_region_dispatch_5min
WHERE interval_end >= TIMESTAMPADD(HOUR, -24, (SELECT MAX(interval_end) FROM {{catalog}}.{{schema}}.gold_nem_region_dispatch_5min))
GROUP BY interval_end, region_id
HAVING COUNT_IF(is_effective_run) <> 1
ORDER BY interval_end DESC, region_id;
