SELECT
  constraint_id,
  MEASURE(binding_constraint_interval_count) AS binding_constraint_interval_count,
  MEASURE(average_marginal_value) AS average_marginal_value,
  MEASURE(maximum_violation_degree) AS maximum_violation_degree
FROM {{catalog}}.{{schema}}.nem_binding_constraint_metrics
WHERE interval_end >= TIMESTAMPADD(HOUR, -24, (SELECT MAX(interval_end) FROM {{catalog}}.{{schema}}.nem_binding_constraint_metrics))
GROUP BY ALL
ORDER BY binding_constraint_interval_count DESC, constraint_id;
