import { z } from 'zod';
import { classifyRows, type QueryState, type RegionStatus } from '../domain/regionStatus';
import type { FuelGenerationRow } from '../domain/fuelCapture';
import type { UnitDispatchRow } from '../domain/facilityMap';
import type { RegionStatusRepository } from './regionStatusRepository';

const requiredNumber = z.preprocess(
  (value) => (typeof value === 'string' && value.trim() !== '' ? Number(value) : value),
  z.number().finite()
);
const optionalNumber = z.preprocess(
  (value) => (typeof value === 'string' && value.trim() !== '' ? Number(value) : value),
  z.number().finite().nullable()
);
const timestamp = z.iso.datetime({ offset: true });

const analyticsRowSchema = z.object({
  region_id: z.string().min(1),
  interval_end: timestamp,
  intervention: requiredNumber,
  rrp_aud_per_mwh: requiredNumber,
  total_demand_mw: requiredNumber,
  price_source_run_no: requiredNumber,
  demand_source_run_no: requiredNumber,
  source_interval_watermark: timestamp,
  source_publication_at: timestamp,
  gold_published_at: timestamp,
  market_wide_binding_constraint_count: requiredNumber,
  market_wide_interconnector_count: requiredNumber,
  market_wide_interconnector_source_sign_flow_mw: requiredNumber,
  prediction_score: optionalNumber,
  prediction_model_version: z.string().nullable(),
  prediction_feature_time: timestamp.nullable(),
  prediction_scored_at: timestamp.nullable(),
  prediction_source_freshness: z.string().nullable(),
  prediction_missing_feature_status: z.string().nullable(),
});

type AnalyticsLoader = () => Promise<unknown[]>;

export function normaliseIntegrationRows(rows: unknown[]): RegionStatus[] {
  return rows.map((candidate) => {
    const row = analyticsRowSchema.parse(candidate);
    return {
      regionId: row.region_id,
      intervalEnd: row.interval_end,
      intervention: row.intervention,
      rrpAudPerMwh: row.rrp_aud_per_mwh,
      totalDemandMw: row.total_demand_mw,
      priceSourceRunNo: row.price_source_run_no,
      demandSourceRunNo: row.demand_source_run_no,
      sourceIntervalWatermark: row.source_interval_watermark,
      sourcePublicationAt: row.source_publication_at,
      goldPublishedAt: row.gold_published_at,
      marketWideBindingConstraintCount: row.market_wide_binding_constraint_count,
      marketWideInterconnectorCount: row.market_wide_interconnector_count,
      marketWideInterconnectorSourceSignFlowMw: row.market_wide_interconnector_source_sign_flow_mw,
      predictionScore: row.prediction_score,
      predictionModelVersion: row.prediction_model_version,
      predictionFeatureTime: row.prediction_feature_time,
      predictionScoredAt: row.prediction_scored_at,
      predictionSourceFreshness: row.prediction_source_freshness,
      predictionMissingFeatureStatus: row.prediction_missing_feature_status,
    };
  });
}

/**
 * fuelRows precedes nowMs so a caller can supply generation without naming an
 * evaluation instant. That keeps `Date.now()` out of render, where it is an
 * impure call, and leaves the default in one place.
 */
export function integrationQueryState(
  data: unknown,
  fuelRows: FuelGenerationRow[] | null = null,
  unitRows: UnitDispatchRow[] | null = null,
  nowMs = Date.now()
): QueryState {
  try {
    if (!Array.isArray(data)) throw new Error('Unexpected analytics payload');
    return classifyRows(normaliseIntegrationRows(data), 'integration', nowMs, fuelRows, unitRows);
  } catch {
    return {
      kind: 'error',
      message: 'The analytics result did not match the governed regional-status contract.',
    };
  }
}

export class IntegrationRegionStatusRepository implements RegionStatusRepository {
  private readonly loader: AnalyticsLoader;

  constructor(loader: AnalyticsLoader) {
    this.loader = loader;
  }

  async load(): Promise<RegionStatus[]> {
    return normaliseIntegrationRows(await this.loader());
  }
}
