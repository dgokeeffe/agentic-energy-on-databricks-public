import type { FuelGenerationRow } from './fuelCapture';
import type { UnitDispatchRow } from './facilityMap';

export type DataMode = 'mock' | 'integration';

export interface RegionStatus {
  regionId: string;
  intervalEnd: string;
  intervention: number;
  rrpAudPerMwh: number;
  totalDemandMw: number;
  priceSourceRunNo: number;
  demandSourceRunNo: number;
  sourceIntervalWatermark: string;
  sourcePublicationAt: string;
  goldPublishedAt: string;
  marketWideBindingConstraintCount: number;
  marketWideInterconnectorCount: number;
  marketWideInterconnectorSourceSignFlowMw: number;
  predictionScore: number | null;
  predictionModelVersion: string | null;
  predictionFeatureTime: string | null;
  predictionScoredAt: string | null;
  predictionSourceFreshness: string | null;
  predictionMissingFeatureStatus: string | null;
}

export type QueryState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'empty' }
  | {
      kind: 'ready';
      rows: RegionStatus[];
      mode: DataMode;
      stale: boolean;
      predictionStale: boolean;
      partial: boolean;
      evaluatedAtMs: number;
      /**
       * Generation by region and fuel, or null when that read is unavailable.
       *
       * Null is a first-class state rather than an empty array: integration mode
       * needs a second Unity Catalog grant for the generation tables, so an
       * unprivileged deployment must degrade the value-capture section while
       * still reporting governed price and freshness.
       */
      fuelRows: FuelGenerationRow[] | null;
      /**
       * Per-unit output for the generator map, or null when unavailable.
       *
       * Null for the same reason as fuelRows: the map needs a third Unity Catalog
       * grant, so a deployment without it must lose the map alone rather than the
       * whole screen.
       */
      unitRows: UnitDispatchRow[] | null;
    };

const SOURCE_STALE_AFTER_MS = 15 * 60 * 1000;

export function isSourceStale(row: RegionStatus, nowMs = Date.now()) {
  return nowMs - Date.parse(row.sourceIntervalWatermark) > SOURCE_STALE_AFTER_MS;
}

export function classifyRows(
  rows: RegionStatus[],
  mode: DataMode,
  nowMs = Date.now(),
  fuelRows: FuelGenerationRow[] | null = null,
  unitRows: UnitDispatchRow[] | null = null
): QueryState {
  if (rows.length === 0) return { kind: 'empty' };

  const newestIntervalMs = Math.max(...rows.map((row) => Date.parse(row.intervalEnd)));
  const latestRows = rows.filter((row) => Date.parse(row.intervalEnd) === newestIntervalMs);
  const partial = latestRows.some((row) => row.predictionScore === null || row.predictionModelVersion === null);
  const stale = latestRows.some((row) => isSourceStale(row, nowMs));
  const predictionStale = latestRows.some(
    (row) => row.predictionSourceFreshness === 'STALE' || row.predictionMissingFeatureStatus === 'STALE'
  );
  return {
    kind: 'ready',
    rows,
    mode,
    stale,
    predictionStale,
    partial,
    evaluatedAtMs: nowMs,
    fuelRows,
    unitRows,
  };
}
