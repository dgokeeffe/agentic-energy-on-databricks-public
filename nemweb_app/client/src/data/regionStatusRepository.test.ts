import { describe, expect, it } from 'vitest';
import { classifyRows, isSourceStale } from '../domain/regionStatus';
import { integrationQueryState, normaliseIntegrationRows } from './integrationRegionStatusRepository';
import { MockRegionStatusRepository } from './mockRegionStatusRepository';

function integrationRow(source: Awaited<ReturnType<MockRegionStatusRepository['load']>>[number]) {
  return {
    region_id: source.regionId,
    interval_end: source.intervalEnd,
    intervention: source.intervention,
    rrp_aud_per_mwh: source.rrpAudPerMwh,
    total_demand_mw: source.totalDemandMw,
    price_source_run_no: source.priceSourceRunNo,
    demand_source_run_no: source.demandSourceRunNo,
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
  };
}

describe('RegionStatusRepository contract', () => {
  it('uses the same camel-case domain shape in mock and integration modes', async () => {
    const mock = await new MockRegionStatusRepository().load();
    const source = mock[0];
    if (!source) throw new Error('prepared fixture must contain a row');
    expect(normaliseIntegrationRows([integrationRow(source)])).toEqual([source]);
  });

  it('classifies freshness and partial state from the newest interval only', async () => {
    expect(classifyRows([], 'mock')).toEqual({ kind: 'empty' });
    const [source] = await new MockRegionStatusRepository().load();
    if (!source) throw new Error('prepared fixture must contain a row');

    const complete = {
      ...source,
      intervalEnd: '2026-07-01T00:10:00+10:00',
      sourceIntervalWatermark: '2026-07-01T00:10:00+10:00',
      predictionScore: 0.2,
      predictionModelVersion: '2',
      predictionSourceFreshness: 'CURRENT',
    };
    const olderStalePartial = {
      ...source,
      intervalEnd: '2026-07-01T00:05:00+10:00',
      sourceIntervalWatermark: '2026-07-01T00:05:00+10:00',
      predictionScore: null,
      predictionModelVersion: null,
      predictionSourceFreshness: 'STALE',
    };
    const now = Date.parse('2026-07-01T00:12:00+10:00');

    expect(classifyRows([olderStalePartial, complete], 'integration', now)).toMatchObject({
      stale: false,
      partial: false,
    });
    expect(
      classifyRows(
        [{ ...complete, sourceIntervalWatermark: '2026-07-01T00:00:00+10:00' }],
        'integration',
        Date.parse('2026-07-01T00:16:00+10:00')
      )
    ).toMatchObject({ stale: true, predictionStale: false });
    expect(
      classifyRows(
        [{ ...complete, predictionSourceFreshness: 'STALE' }],
        'integration',
        Date.parse('2026-07-01T00:12:00+10:00')
      )
    ).toMatchObject({ stale: false, predictionStale: true });
    expect(
      isSourceStale(
        { ...complete, sourceIntervalWatermark: '2026-07-01T00:00:00+10:00' },
        Date.parse('2026-07-01T00:16:00+10:00')
      )
    ).toBe(true);
  });

  it('turns malformed integration results into a controlled operator error', async () => {
    const [source] = await new MockRegionStatusRepository().load();
    if (!source) throw new Error('prepared fixture must contain a row');
    const valid = integrationRow(source);

    expect(() => normaliseIntegrationRows([{ ...valid, rrp_aud_per_mwh: null }])).toThrow();
    expect(() => normaliseIntegrationRows([{ ...valid, source_publication_at: 'not-a-timestamp' }])).toThrow();
    expect(() => normaliseIntegrationRows([{ ...valid, interval_end: '2026-02-30T00:00:00+10:00' }])).toThrow();
    expect(() => normaliseIntegrationRows([{ ...valid, prediction_feature_time: 'not-a-timestamp' }])).toThrow();
    for (const data of [[{ ...valid, rrp_aud_per_mwh: null }], { unexpected: true }]) {
      expect(integrationQueryState(data)).toEqual({
        kind: 'error',
        message: 'The analytics result did not match the governed regional-status contract.',
      });
    }
  });
});
