-- NEM DISPATCHIS analytics suite
--
-- Runs against DISPATCHIS history backfilled by scripts/backfill-nem-history.py
-- and landed in a Unity Catalog volume under:
--   /Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/
--
-- BEFORE RUNNING: substitute ${catalog}, ${schema}, and ${landing_volume} for
-- your target's values. They are intentionally left as placeholders because
-- this repo never commits workspace-specific catalog, schema, or volume names
-- (see databricks.yml and .env.example) -- supply them the same way the bundle
-- does, via BUNDLE_VAR_* or your editor's find-and-replace.
--
-- The data is Hive-partitioned as dispatch_date=YYYY-MM-DD, so predicates on
-- dispatch_date prune partitions. No UC table is required -- these read the
-- JSONL files directly via the json.`path` syntax. That matters when the
-- running principal has READ_VOLUME but not CREATE TABLE on the schema, which
-- is the normal case for a landing catalog: you can still do full SQL
-- analytics, you just cannot register tables or point Genie at them.
--
-- Verified coverage when these were written: 43,200 rows / 8,640 intervals /
-- 31 days (2026-07-12 .. 2026-08-11), 5 NEM regions, no gaps, no duplicate
-- natural keys, no null prices or demand.
--
-- NOTE ON DAY BOUNDARIES: AEMO's daily archive PUBLIC_DISPATCHIS_<YYYYMMDD>.zip
-- spans 00:05..24:00, so its final interval (00:00) belongs to the NEXT calendar
-- day. dispatch_date here is derived from interval_datetime, not the filename,
-- so per-day aggregates can differ by one interval from filename-based counts.
-- This is deliberate and the interval-based attribution is the correct one.
--
-- Usage (Databricks SQL warehouse, or the CLI):
--   databricks api post /api/2.0/sql/statements --json '{"warehouse_id":"...","statement":"<query>"}'

-- ---------------------------------------------------------------------------
-- A0. Coverage / freshness guard. Run this first, and stop if counts look off.
-- ---------------------------------------------------------------------------
SELECT COUNT(*)                        AS rows,
       COUNT(DISTINCT interval_datetime) AS intervals,
       COUNT(DISTINCT dispatch_date)   AS days,
       COUNT(DISTINCT region)          AS regions,
       MIN(dispatch_date)              AS first_day,
       MAX(dispatch_date)              AS last_day
FROM json.`/Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/`;

-- ---------------------------------------------------------------------------
-- A1. Price duration curve. Percentiles matter more than the mean here: the
-- distribution is heavy-tailed, so mean alone hides both the negative floor
-- and the spike tail.
-- ---------------------------------------------------------------------------
SELECT region,
       ROUND(percentile(price_per_mwh, 0.01),  2) AS p1,
       ROUND(percentile(price_per_mwh, 0.10),  2) AS p10,
       ROUND(percentile(price_per_mwh, 0.50),  2) AS median,
       ROUND(percentile(price_per_mwh, 0.90),  2) AS p90,
       ROUND(percentile(price_per_mwh, 0.99),  2) AS p99,
       ROUND(percentile(price_per_mwh, 0.999), 2) AS p999,
       ROUND(AVG(price_per_mwh), 2)              AS mean
FROM json.`/Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/`
GROUP BY region
ORDER BY median DESC;

-- ---------------------------------------------------------------------------
-- A2. Volatility and cost concentration. pct_cost_from_spikes is the headline
-- risk number: share of total energy cost (price x demand) incurred while
-- price > $300/MWh, versus the share of time spent there.
-- ---------------------------------------------------------------------------
WITH b AS (
  SELECT region, price_per_mwh AS p, demand_mw AS d
  FROM json.`/Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/`
)
SELECT region,
       ROUND(STDDEV(p), 1)                                             AS price_stddev,
       ROUND(STDDEV(p) / NULLIF(AVG(p), 0), 2)                         AS coeff_var,
       ROUND(percentile(p, 0.99) / NULLIF(percentile(p, 0.5), 0), 1)   AS p99_to_median,
       ROUND(100.0 * SUM(CASE WHEN p > 300 THEN p * d ELSE 0 END)
             / NULLIF(SUM(p * d), 0), 1)                               AS pct_cost_from_spikes,
       ROUND(100.0 * SUM(CASE WHEN p > 300 THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                            AS pct_time_spiking
FROM b
GROUP BY region
ORDER BY coeff_var DESC;

-- ---------------------------------------------------------------------------
-- A3. Ramp rates: 5-minute deltas in demand and price. Large price jumps with
-- small demand ramps indicate supply-side (bidding / outage) events rather
-- than load events.
-- ---------------------------------------------------------------------------
WITH s AS (
  SELECT region, interval_datetime, demand_mw, price_per_mwh,
         demand_mw     - LAG(demand_mw)     OVER (PARTITION BY region ORDER BY interval_datetime) AS d_ramp,
         price_per_mwh - LAG(price_per_mwh) OVER (PARTITION BY region ORDER BY interval_datetime) AS p_jump
  FROM json.`/Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/`
)
SELECT region,
       ROUND(MAX(d_ramp), 0)                  AS max_ramp_up_mw_5min,
       ROUND(MIN(d_ramp), 0)                  AS max_ramp_down_mw,
       ROUND(percentile(ABS(d_ramp), 0.99), 0) AS p99_abs_ramp,
       ROUND(MAX(p_jump), 0)                  AS biggest_price_jump,
       ROUND(MIN(p_jump), 0)                  AS biggest_price_drop
FROM s
WHERE d_ramp IS NOT NULL
GROUP BY region
ORDER BY p99_abs_ramp DESC;

-- ---------------------------------------------------------------------------
-- A4. Peak vs off-peak. AEMO convention: weekday 07:00-22:00 is peak.
-- demand_wtd_price is what a flat-load buyer actually pays, which differs from
-- the simple average whenever price and demand are correlated.
-- ---------------------------------------------------------------------------
WITH b AS (
  SELECT region, price_per_mwh AS p, demand_mw AS d,
         CAST(substr(interval_datetime, 12, 2) AS INT)   AS hh,
         date_format(to_date(dispatch_date), 'E')        AS dow
  FROM json.`/Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/`
),
f AS (SELECT *, (hh >= 7 AND hh < 22 AND dow NOT IN ('Sat','Sun')) AS is_peak FROM b)
SELECT region,
       ROUND(AVG(CASE WHEN is_peak      THEN p END), 2) AS peak_price,
       ROUND(AVG(CASE WHEN NOT is_peak  THEN p END), 2) AS offpeak_price,
       ROUND(AVG(CASE WHEN is_peak      THEN p END)
           - AVG(CASE WHEN NOT is_peak  THEN p END), 2) AS peak_premium,
       ROUND(SUM(p * d) / NULLIF(SUM(d), 0), 2)         AS demand_wtd_price
FROM f
GROUP BY region
ORDER BY peak_premium DESC;

-- ---------------------------------------------------------------------------
-- A5. Spike clustering. Spikes are not spread evenly: they concentrate on a
-- few days, which is why a short sample window badly understates tail risk.
-- ---------------------------------------------------------------------------
WITH s AS (
  SELECT region, dispatch_date
  FROM json.`/Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/`
  WHERE price_per_mwh > 300
)
SELECT region,
       COUNT(*)                                                   AS spike_intervals,
       COUNT(DISTINCT dispatch_date)                              AS spike_days,
       ROUND(1.0 * COUNT(*) / NULLIF(COUNT(DISTINCT dispatch_date), 0), 1) AS spikes_per_spike_day,
       MIN(dispatch_date)                                         AS first_spike_day,
       MAX(dispatch_date)                                         AS last_spike_day
FROM s
GROUP BY region
ORDER BY spike_intervals DESC;

-- ---------------------------------------------------------------------------
-- A6. Diurnal profile: the solar duck curve. Expect a midday price trough with
-- many negative intervals, then a sharp evening ramp as PV output falls away.
-- ---------------------------------------------------------------------------
SELECT CAST(substr(interval_datetime, 12, 2) AS INT)                  AS hour_local,
       ROUND(AVG(price_per_mwh), 2)                                   AS avg_price,
       ROUND(SUM(demand_mw) / COUNT(DISTINCT interval_datetime), 0)   AS avg_nem_demand,
       SUM(CASE WHEN price_per_mwh < 0 THEN 1 ELSE 0 END)             AS neg_count
FROM json.`/Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/`
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- A7. Inter-regional price correlation. Weak coupling implies interconnector
-- constraints binding, whereas strong coupling implies a shared market.
-- ---------------------------------------------------------------------------
WITH p AS (
  SELECT interval_datetime,
         MAX(CASE WHEN region = 'NSW1' THEN price_per_mwh END) AS nsw,
         MAX(CASE WHEN region = 'QLD1' THEN price_per_mwh END) AS qld,
         MAX(CASE WHEN region = 'VIC1' THEN price_per_mwh END) AS vic,
         MAX(CASE WHEN region = 'SA1'  THEN price_per_mwh END) AS sa,
         MAX(CASE WHEN region = 'TAS1' THEN price_per_mwh END) AS tas
  FROM json.`/Volumes/${catalog}/${schema}/${landing_volume}/live/history/dispatchis/`
  GROUP BY interval_datetime
)
SELECT ROUND(corr(nsw, qld), 3) AS nsw_qld,
       ROUND(corr(nsw, vic), 3) AS nsw_vic,
       ROUND(corr(nsw, sa),  3) AS nsw_sa,
       ROUND(corr(vic, sa),  3) AS vic_sa,
       ROUND(corr(vic, tas), 3) AS vic_tas
FROM p;
