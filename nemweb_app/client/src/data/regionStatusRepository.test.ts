import { describe, expect, it } from 'vitest';
import { classifyRows } from '../domain/regionStatus';
import { normaliseIntegrationRows } from './integrationRegionStatusRepository';
import { MockRegionStatusRepository } from './mockRegionStatusRepository';

describe('RegionStatusRepository contract', () => {
  it('uses the same camel-case domain shape in mock and integration modes', async () => {
    const mock = await new MockRegionStatusRepository().load();
    const source = mock[0];
    if (!source) throw new Error('prepared fixture must contain a row');
    const integration = normaliseIntegrationRows([
      {
        region_id: source.regionId,
        interval_end: source.intervalEnd,
        intervention: source.intervention,
        rrp_aud_per_mwh: source.rrpAudPerMwh,
        total_demand_mw: source.totalDemandMw,
        source_interval_watermark: source.sourceIntervalWatermark,
        source_publication_at: source.sourcePublicationAt,
        gold_published_at: source.goldPublishedAt,
        market_wide_binding_constraint_count: source.marketWideBindingConstraintCount,
        market_wide_interconnector_count: source.marketWideInterconnectorCount,
        market_wide_interconnector_source_sign_flow_mw: source.marketWideInterconnectorSourceSignFlowMw,
        prediction_score: source.predictionScore,
        prediction_model_version: source.predictionModelVersion,
        prediction_feature_time: source.predictionFeatureTime,
        prediction_scored_at: source.predictionScoredAt,
        prediction_source_freshness: source.predictionSourceFreshness,
        prediction_missing_feature_status: source.predictionMissingFeatureStatus,
      },
    ]);
    expect(integration).toEqual([source]);
  });

  it('classifies empty, partial, and stale results explicitly', async () => {
    expect(classifyRows([], 'mock')).toEqual({ kind: 'empty' });
    const [row] = await new MockRegionStatusRepository().load();
    if (!row) throw new Error('prepared fixture must contain a row');
    expect(classifyRows([{ ...row, predictionScore: null }], 'mock')).toMatchObject({
      partial: true,
    });
    expect(classifyRows([{ ...row, predictionSourceFreshness: 'STALE' }], 'integration')).toMatchObject({
      stale: true,
    });
  });

  it('rejects malformed integration rows instead of rendering misleading values', () => {
    expect(() => normaliseIntegrationRows([{ region_id: 'NSW1' }])).toThrow();
  });
});
