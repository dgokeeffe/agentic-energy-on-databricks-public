import { z } from 'zod';
import type { RegionStatus } from '../domain/regionStatus';
import type { RegionStatusRepository } from './regionStatusRepository';

const analyticsRowSchema = z.object({
  region_id: z.string(),
  interval_end: z.string(),
  intervention: z.coerce.number(),
  rrp_aud_per_mwh: z.coerce.number(),
  total_demand_mw: z.coerce.number(),
  source_interval_watermark: z.string(),
  source_publication_at: z.string(),
  gold_published_at: z.string(),
  market_wide_binding_constraint_count: z.coerce.number(),
  market_wide_interconnector_count: z.coerce.number(),
  market_wide_interconnector_source_sign_flow_mw: z.coerce.number(),
  prediction_score: z.coerce.number().nullable(),
  prediction_model_version: z.string().nullable(),
  prediction_feature_time: z.string().nullable(),
  prediction_scored_at: z.string().nullable(),
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

export class IntegrationRegionStatusRepository implements RegionStatusRepository {
  private readonly loader: AnalyticsLoader;

  constructor(loader: AnalyticsLoader) {
    this.loader = loader;
  }

  async load(): Promise<RegionStatus[]> {
    return normaliseIntegrationRows(await this.loader());
  }
}
