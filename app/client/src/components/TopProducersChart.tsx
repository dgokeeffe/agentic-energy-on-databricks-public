import { useMemo } from 'react';
import { BarChart } from '@databricks/appkit-ui/react';
import facilitiesJson from '../data/topology/nemFacilities.json';
import { fuelLabel, fuelToken, type FuelToken } from '../domain/fuelCapture';
import { latestIntervalRows, type NemFacility, type UnitDispatchRow } from '../domain/facilityMap';

/**
 * Top generating stations by output for the latest interval.
 *
 * After the GridSense Intelligence Hub's LiveNemGenerationChart, keeping the
 * part of its reasoning that matters: lead with the fields that are trustworthy
 * — total output and the named units — and colour each bar by fuel. That app
 * deliberately omits a fuel-mix pie because its per-unit lookup only covers
 * large stations, leaving a misleading "Other" bucket. Here the enrichment is
 * governed, so unmatched units are reported explicitly instead of being pooled.
 *
 * Two corrections against a first version of this component, both caught by
 * reading the rendered screen:
 *
 *  1. It ranked per DUID but labelled per facility, so a four-unit station
 *     appeared as four identical bars ("Bayswater, Bayswater, Bayswater").
 *     Output is now summed to the station, which is also the unit an operator
 *     thinks in.
 *  2. Colour is carried by one series per fuel rather than a per-bar colour
 *     array. AppKit maps `colors` to series, not to categories, so the array
 *     form silently gave every bar the first colour.
 */

const TOP_N = 12;

interface FacilityIndexEntry {
  facilityName: string;
  regionId: string;
}

/** DUID to facility, from the same static reference the map uses. */
const FACILITY_BY_DUID: Map<string, FacilityIndexEntry> = new Map(
  (facilitiesJson as NemFacility[]).flatMap((facility) =>
    facility.duids.map((duid) => [duid, { facilityName: facility.facilityName, regionId: facility.regionId }] as const)
  )
);

function readTokenColour(token: FuelToken): string {
  if (typeof window === 'undefined' || typeof getComputedStyle !== 'function') return '#6a6a6a';
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--fuel-${token}`).trim();
  return value || '#6a6a6a';
}

function unitToken(row: UnitDispatchRow): FuelToken {
  const token = fuelToken(row.fuelType);
  if (token === 'battery_discharging' && row.actualGenerationMw < 0) return 'battery_charging';
  return token;
}

export interface TopProducersChartProps {
  /** Governed per-unit rows, or null when the read is unavailable. */
  rows: UnitDispatchRow[] | null;
}

export function TopProducersChart({ rows }: TopProducersChartProps) {
  const { data, fuelKeys, colours, totalMw, unitCount, unmatchedCount } = useMemo(() => {
    const latest = rows ? latestIntervalRows(rows) : [];

    // Sum to the station. A DUID with no known facility keeps its own identity
    // rather than being pooled, so it stays visible and attributable.
    interface Station {
      label: string;
      byToken: Map<FuelToken, number>;
      net: number;
    }
    const stations = new Map<string, Station>();
    for (const row of latest) {
      const known = FACILITY_BY_DUID.get(row.duid);
      const key = known ? known.facilityName : row.duid;
      const station = stations.get(key) ?? { label: key, byToken: new Map(), net: 0 };
      const token = unitToken(row);
      station.byToken.set(token, (station.byToken.get(token) ?? 0) + row.actualGenerationMw);
      station.net += row.actualGenerationMw;
      stations.set(key, station);
    }

    // Rank by net output, then reverse so the largest sits at the top of a
    // horizontal chart.
    const ranked = [...stations.values()]
      .sort((a, b) => b.net - a.net)
      .slice(0, TOP_N)
      .reverse();

    // One series per fuel present, so AppKit's series-indexed colours line up.
    const tokensPresent = [...new Set(ranked.flatMap((station) => [...station.byToken.keys()]))].sort();

    const series = ranked.map((station) => {
      const point: Record<string, string | number> = { station: station.label };
      for (const token of tokensPresent) {
        point[fuelLabel(token)] = Number((station.byToken.get(token) ?? 0).toFixed(1));
      }
      return point;
    });

    return {
      data: series,
      fuelKeys: tokensPresent.map((token) => fuelLabel(token)),
      colours: tokensPresent.map(readTokenColour),
      totalMw: latest.reduce((sum, row) => sum + row.actualGenerationMw, 0),
      unitCount: latest.length,
      unmatchedCount: latest.filter((row) => row.dimensionMatchStatus !== 'MATCHED').length,
    };
  }, [rows]);

  if (rows === null) {
    return (
      <section className="panel" aria-labelledby="top-units-title">
        <div className="panel-head">
          <div>
            <p className="section-kicker">Observe</p>
            <h2 id="top-units-title" className="panel-title">
              Top producers
            </h2>
          </div>
        </div>
        <p className="panel-empty">
          The governed per-unit read is unavailable, so no station ranking is shown. This surface needs{' '}
          <code>SELECT</code> on <code>gold_nem_unit_dispatch_5min</code>.
        </p>
      </section>
    );
  }

  if (data.length === 0) {
    return (
      <section className="panel" aria-labelledby="top-units-title">
        <div className="panel-head">
          <div>
            <p className="section-kicker">Observe</p>
            <h2 id="top-units-title" className="panel-title">
              Top producers
            </h2>
          </div>
        </div>
        <p className="panel-empty">No unit observations for this interval.</p>
      </section>
    );
  }

  const totalGw = Math.abs(totalMw) >= 1000;

  return (
    <section className="panel" aria-labelledby="top-units-title">
      <div className="panel-head">
        <div>
          <p className="section-kicker">Observe</p>
          <h2 id="top-units-title" className="panel-title">
            Top producers
          </h2>
          <p className="panel-note">
            Highest {Math.min(TOP_N, data.length)} stations by metered output in the latest interval, summed across
            their units and coloured by fuel.
          </p>
        </div>
        <p className="panel-figure numeric">
          {totalGw ? `${(totalMw / 1000).toFixed(2)} GW` : `${Math.round(totalMw)} MW`}
          <small>
            {unitCount.toLocaleString('en-AU')} units reporting
            {unmatchedCount > 0 ? ` · ${unmatchedCount} unenriched` : ''}
          </small>
        </p>
      </div>

      <BarChart
        data={data}
        xKey="station"
        yKey={fuelKeys}
        orientation="horizontal"
        colors={colours}
        stacked
        height={320}
        showLegend={fuelKeys.length > 1}
      />

      <p className="panel-boundary">
        Per-DUID metered output, summed to the station where a facility name is known and left under its DUID where it
        is not. Region and fuel come from the governed monthly facility dimension; an unenriched unit is counted above
        rather than pooled into another fuel.
      </p>
    </section>
  );
}
