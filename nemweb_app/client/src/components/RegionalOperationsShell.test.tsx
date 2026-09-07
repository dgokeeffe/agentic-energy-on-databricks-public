import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { RegionalOperationsShell } from './RegionalOperationsShell';
import type { RegionStatus } from '../domain/regionStatus';

const row: RegionStatus = {
  regionId: 'NSW1',
  intervalEnd: '2026-07-01T00:05:00+10:00',
  intervention: 0,
  rrpAudPerMwh: 128.5,
  totalDemandMw: 8123.4,
  sourceIntervalWatermark: '2026-07-01T00:05:00+10:00',
  sourcePublicationAt: '2026-07-01T00:06:00+10:00',
  goldPublishedAt: '2026-06-30T14:07:00Z',
  marketWideBindingConstraintCount: 3,
  marketWideInterconnectorCount: 6,
  marketWideInterconnectorSourceSignFlowMw: -42.5,
  predictionScore: 0.2,
  predictionModelVersion: '2',
  predictionFeatureTime: '2026-07-01T00:05:00+10:00',
  predictionScoredAt: '2026-06-30T14:07:30Z',
  predictionSourceFreshness: 'CURRENT',
  predictionMissingFeatureStatus: 'COMPLETE',
};

const render = (state: Parameters<typeof RegionalOperationsShell>[0]['state']) =>
  renderToStaticMarkup(<RegionalOperationsShell state={state} />);

describe('RegionalOperationsShell', () => {
  it('renders loading, empty, and error states', () => {
    expect(render({ kind: 'loading' })).toContain('Loading regional conditions');
    expect(render({ kind: 'empty' })).toContain('No regional conditions');
    expect(render({ kind: 'error', message: 'warehouse unavailable' })).toContain('warehouse unavailable');
  });

  it('renders prepared, partial, stale, and healthy states with source labels', () => {
    const partial = render({
      kind: 'ready',
      rows: [{ ...row, predictionScore: null }],
      mode: 'mock',
      partial: true,
      stale: false,
    });
    expect(partial).toContain('Prepared non-live fixture');
    expect(partial).toContain('Partial result');
    const stale = render({ kind: 'ready', rows: [row], mode: 'integration', partial: false, stale: true });
    expect(stale).toContain('Stale source');
    const healthy = render({ kind: 'ready', rows: [row], mode: 'integration', partial: false, stale: false });
    expect(healthy).toContain('Current NEM regional conditions');
    expect(healthy).toContain('NEMWEB publication');
    expect(healthy).toContain('Gold publication');
  });

  it('labels repeated market-wide source-sign flow without regional direction', () => {
    const html = render({ kind: 'ready', rows: [row], mode: 'integration', partial: false, stale: false });
    expect(html).toContain('market-wide, AEMO source sign, MW');
    expect(html).toContain('No regional allocation or directional interpretation');
  });
});
