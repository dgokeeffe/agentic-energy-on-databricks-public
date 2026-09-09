import { useMemo } from 'react';
import { AreaChart } from '@databricks/appkit-ui/react';
import { fuelLabel, fuelToken, type FuelToken } from '../domain/fuelCapture';
import type { FuelGenerationRow } from '../domain/fuelCapture';

/**
 * Generation over time, stacked by fuel.
 *
 * After the GridSense Intelligence Hub's GenerationOverTimeChart, which is
 * itself the Open Electricity tracker look. Two deliberate differences:
 *
 *  - It uses AppKit's echarts-backed AreaChart rather than recharts. recharts is
 *    not a dependency here and adding one for a single chart is not worth it;
 *    AppKit already ships charts on the echarts instance it owns.
 *  - Colour comes from this app's existing fuel tokens rather than a second
 *    palette, so this chart, the value-capture bars and the generator map cannot
 *    disagree about what brown coal looks like.
 *
 * Signed values are summed as published: a charging battery is negative, so it
 * subtracts from the stack rather than being shown as generation. Stacked areas
 * with negatives are legitimate here because the total is net supply.
 */

/** Stack order, heaviest baseload at the bottom, matching Open Electricity. */
const STACK_ORDER: readonly FuelToken[] = [
  'coal_black',
  'coal_brown',
  'gas',
  'distillate',
  'bioenergy_biomass',
  'hydro',
  'wind',
  'solar_utility',
  'battery_discharging',
  'battery_charging',
  'unknown',
] as const;

function readTokenColour(token: FuelToken): string {
  if (typeof window === 'undefined' || typeof getComputedStyle !== 'function') return '#6a6a6a';
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--fuel-${token}`).trim();
  return value || '#6a6a6a';
}

/** Interval-ending label in fixed market time, read from the string. */
function intervalLabel(intervalEnd: string): string {
  const match = /[T ](\d{2}):(\d{2})/.exec(intervalEnd);
  return match ? `${match[1]}:${match[2]}` : intervalEnd;
}

export interface GenerationByFuelChartProps {
  /** Governed generation rows, or null when the read is unavailable. */
  rows: FuelGenerationRow[] | null;
  /** Restrict to one region, or omit for the whole NEM. */
  regionId?: string;
}

export function GenerationByFuelChart({ rows, regionId }: GenerationByFuelChartProps) {
  const { data, tokens, latestTotalMw, intervalCount } = useMemo(() => {
    const scoped = (rows ?? []).filter((row) => !regionId || row.regionId === regionId);

    // One row per interval, one column per fuel present.
    const byInterval = new Map<string, Map<FuelToken, number>>();
    const present = new Set<FuelToken>();
    for (const row of scoped) {
      const token = fuelToken(row.fuelType);
      // Charging is a distinct display token, resolved from the sign, matching
      // observationToken in fuelCapture.ts.
      const resolved: FuelToken =
        token === 'battery_discharging' && row.actualGenerationMw < 0 ? 'battery_charging' : token;
      present.add(resolved);
      const bucket = byInterval.get(row.intervalEnd) ?? new Map<FuelToken, number>();
      bucket.set(resolved, (bucket.get(resolved) ?? 0) + row.actualGenerationMw);
      byInterval.set(row.intervalEnd, bucket);
    }

    const ordered = STACK_ORDER.filter((token) => present.has(token));
    const intervals = [...byInterval.keys()].sort((left, right) => Date.parse(left) - Date.parse(right));

    const series = intervals.map((intervalEnd) => {
      const bucket = byInterval.get(intervalEnd)!;
      const point: Record<string, string | number> = { interval: intervalLabel(intervalEnd) };
      for (const token of ordered) point[fuelLabel(token)] = Number((bucket.get(token) ?? 0).toFixed(1));
      return point;
    });

    const last = intervals.at(-1);
    const total = last ? [...byInterval.get(last)!.values()].reduce((sum, value) => sum + value, 0) : 0;

    return { data: series, tokens: ordered, latestTotalMw: total, intervalCount: intervals.length };
  }, [rows, regionId]);

  if (rows === null) {
    return (
      <section className="panel" aria-labelledby="fuel-chart-title">
        <div className="panel-head">
          <div>
            <p className="section-kicker">Observe</p>
            <h2 id="fuel-chart-title" className="panel-title">
              Generation by fuel
            </h2>
          </div>
        </div>
        <p className="panel-empty">The governed generation read is unavailable, so no fuel mix is shown.</p>
      </section>
    );
  }

  if (data.length === 0) {
    return (
      <section className="panel" aria-labelledby="fuel-chart-title">
        <div className="panel-head">
          <div>
            <p className="section-kicker">Observe</p>
            <h2 id="fuel-chart-title" className="panel-title">
              Generation by fuel
            </h2>
          </div>
        </div>
        <p className="panel-empty">No generation observations for this window.</p>
      </section>
    );
  }

  const totalGw = Math.abs(latestTotalMw) >= 1000;

  return (
    <section className="panel" aria-labelledby="fuel-chart-title">
      <div className="panel-head">
        <div>
          <p className="section-kicker">Observe</p>
          <h2 id="fuel-chart-title" className="panel-title">
            Generation by fuel
          </h2>
          <p className="panel-note">
            Five-minute SCADA output{regionId ? ` in ${regionId}` : ' across the NEM'}, stacked by fuel.
            Interval-ending, fixed AEST.
          </p>
        </div>
        <p className="panel-figure numeric">
          {totalGw ? `${(latestTotalMw / 1000).toFixed(2)} GW` : `${Math.round(latestTotalMw)} MW`}
          <small>latest interval · {intervalCount} shown</small>
        </p>
      </div>

      <AreaChart
        data={data}
        xKey="interval"
        yKey={tokens.map((token) => fuelLabel(token))}
        colors={tokens.map(readTokenColour)}
        stacked
        smooth={false}
        showSymbol={false}
        height={300}
        showLegend
      />

      <p className="panel-boundary">
        Actual metered output, never a dispatch target. AEMO Current publishes no five-minute availability, so this
        cannot show curtailment. A charging battery is negative and reduces the stack.
      </p>
    </section>
  );
}
