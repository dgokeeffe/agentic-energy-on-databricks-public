export type DataMode = 'mock' | 'integration';

export interface RegionStatus {
  regionId: string;
  intervalEnd: string;
  intervention: number;
  rrpAudPerMwh: number;
  totalDemandMw: number;
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
  | { kind: 'ready'; rows: RegionStatus[]; mode: DataMode; stale: boolean; partial: boolean };

export function classifyRows(rows: RegionStatus[], mode: DataMode): QueryState {
  if (rows.length === 0) return { kind: 'empty' };
  const partial = rows.some((row) => row.predictionScore === null || row.predictionModelVersion === null);
  const stale = rows.some(
    (row) => row.predictionSourceFreshness === 'STALE' || row.predictionMissingFeatureStatus === 'STALE'
  );
  return { kind: 'ready', rows, mode, stale, partial };
}
