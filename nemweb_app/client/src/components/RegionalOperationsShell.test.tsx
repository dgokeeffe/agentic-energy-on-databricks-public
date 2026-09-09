import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { RegionalOperationsShell } from './RegionalOperationsShell';
import type { QueryState, RegionStatus } from '../domain/regionStatus';
import type { FuelGenerationRow } from '../domain/fuelCapture';

const row: RegionStatus = {
  regionId: 'NSW1',
  intervalEnd: '2026-07-01T12:05:00+10:00',
  intervention: 0,
  rrpAudPerMwh: 128.5,
  totalDemandMw: 8123.4,
  priceSourceRunNo: 2,
  demandSourceRunNo: 1,
  sourceIntervalWatermark: '2026-07-01T12:05:00+10:00',
  sourcePublicationAt: '2026-07-01T12:06:00+10:00',
  goldPublishedAt: '2026-07-01T02:07:00Z',
  marketWideBindingConstraintCount: 3,
  marketWideInterconnectorCount: 6,
  marketWideInterconnectorSourceSignFlowMw: -42.5,
  predictionScore: 0.2,
  predictionModelVersion: '2',
  predictionFeatureTime: '2026-07-01T12:05:00+10:00',
  predictionScoredAt: '2026-07-01T02:07:30Z',
  predictionSourceFreshness: 'CURRENT',
  predictionMissingFeatureStatus: 'COMPLETE',
};

const fuel = (overrides: Partial<FuelGenerationRow> = {}): FuelGenerationRow => ({
  intervalEnd: '2026-07-01T12:05:00+10:00',
  regionId: 'NSW1',
  fuelType: 'Black coal',
  actualGenerationMw: 1200,
  facilityCount: 4,
  partiallyEnrichedFacilityCount: 0,
  ...overrides,
});

type ReadyState = Extract<QueryState, { kind: 'ready' }>;

const ready = (rows: RegionStatus[], overrides: Partial<Omit<ReadyState, 'kind' | 'rows'>> = {}): ReadyState => ({
  kind: 'ready',
  rows,
  mode: 'integration',
  partial: false,
  stale: false,
  predictionStale: false,
  evaluatedAtMs: Date.parse('2026-07-01T12:10:00+10:00'),
  fuelRows: null,
  unitRows: null,
  ...overrides,
});

const render = (state: Parameters<typeof RegionalOperationsShell>[0]['state']) =>
  renderToStaticMarkup(<RegionalOperationsShell state={state} />);

/** Two intervals with a cheap and a dear price, so capture rates differ. */
const twoIntervals: RegionStatus[] = [
  { ...row, intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 20, priceSourceRunNo: 1 },
  {
    ...row,
    intervalEnd: '2026-07-01T12:10:00+10:00',
    sourceIntervalWatermark: '2026-07-01T12:10:00+10:00',
    rrpAudPerMwh: 180,
    priceSourceRunNo: 1,
  },
];

describe('RegionalOperationsShell', () => {
  it('renders loading, empty, and error states', () => {
    expect(render({ kind: 'loading' })).toContain('Loading regional conditions');
    expect(render({ kind: 'empty' })).toContain('No regional conditions');
    expect(render({ kind: 'error', message: 'warehouse unavailable' })).toContain('warehouse unavailable');
  });

  it('leads with the weakest capturing fuel and its rate', () => {
    const html = render(
      ready(twoIntervals, {
        fuelRows: [
          // Solar runs only in the cheap interval, so it captures least.
          fuel({ fuelType: 'Solar', actualGenerationMw: 900, intervalEnd: '2026-07-01T12:05:00+10:00' }),
          fuel({ fuelType: 'Solar', actualGenerationMw: 0, intervalEnd: '2026-07-01T12:10:00+10:00' }),
          fuel({ fuelType: 'Black coal', actualGenerationMw: 1200, intervalEnd: '2026-07-01T12:05:00+10:00' }),
          fuel({ fuelType: 'Black coal', actualGenerationMw: 1200, intervalEnd: '2026-07-01T12:10:00+10:00' }),
        ],
      })
    );
    expect(html).toContain('Solar (utility)');
    expect(html).toContain('of the NSW1 average price');
    expect(html).toContain('0.20×');
    expect(html).toContain('What each fuel earned in NSW1');
    expect(html).toContain('Indicative energy revenue');
    expect(html).toContain('Regional time-weighted price');
  });

  it('states the purpose, the audience, and the curtailment boundary', () => {
    const html = render(ready(twoIntervals, { fuelRows: [fuel()] }));
    expect(html).toContain('Find where the value went');
    expect(html).toContain('portfolio analyst or asset performance team');
    expect(html).toContain('What it cannot tell you');
    // The most likely misreading of a capture screen is that it measures
    // curtailment, so the denial has to be on the page.
    expect(html).toContain('Curtailment');
    expect(html).toContain('no five-minute availability');
  });

  it('attributes the borrowed design system and disclaims affiliation', () => {
    const html = render(ready(twoIntervals, { fuelRows: [fuel()] }));
    expect(html).toContain('Open Electricity');
    expect(html).toContain('MIT licensed');
    expect(html).toContain('not affiliated with, endorsed by, or produced for');
    expect(html).toContain('never live market evidence');
    // The retired AGL theme must not leave a stale claim behind.
    expect(html).not.toContain('AGL');
  });

  it('reports revenue as indicative rather than settlement value', () => {
    const html = render(ready(twoIntervals, { fuelRows: [fuel()] }));
    expect(html).toContain('excluding FCAS, loss factors, contracts, and settlement adjustment');
  });

  it('degrades the capture section without losing price reporting when generation is unavailable', () => {
    const html = render(ready(twoIntervals, { fuelRows: null }));
    expect(html).toContain('Generation read unavailable');
    expect(html).toContain('lacks SELECT on the governed generation tables');
    expect(html).toContain('Value capture is unavailable for NSW1');
    // Governed price and freshness must survive the loss of the second read.
    expect(html).toContain('Underlying five-minute prices');
    expect(html).toContain('Source and freshness · NSW1');
  });

  it('reports negative-price exposure as a loss for a generator', () => {
    const html = render(
      ready(
        [
          { ...row, intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: -40, priceSourceRunNo: 1 },
          {
            ...row,
            intervalEnd: '2026-07-01T12:10:00+10:00',
            sourceIntervalWatermark: '2026-07-01T12:10:00+10:00',
            rrpAudPerMwh: 120,
            priceSourceRunNo: 1,
          },
        ],
        {
          fuelRows: [
            fuel({ fuelType: 'Solar', actualGenerationMw: 1200, intervalEnd: '2026-07-01T12:05:00+10:00' }),
            fuel({ fuelType: 'Solar', actualGenerationMw: 1200, intervalEnd: '2026-07-01T12:10:00+10:00' }),
          ],
        }
      )
    );
    expect(html).toContain('Negative-price exposure');
    expect(html).toContain('AUD lost');
    // 100 MWh × −$40 = −$4,000, rendered with an explicit minus sign.
    expect(html).toContain('−A$4,000');
    expect(html).toContain('1 of 2 intervals below zero');
  });

  it('withholds capture rates when the regional time-weighted price is not positive', () => {
    const html = render(
      ready(
        [
          { ...row, intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: -60, priceSourceRunNo: 1 },
          {
            ...row,
            intervalEnd: '2026-07-01T12:10:00+10:00',
            sourceIntervalWatermark: '2026-07-01T12:10:00+10:00',
            rrpAudPerMwh: -20,
            priceSourceRunNo: 1,
          },
        ],
        { fuelRows: [fuel(), fuel({ intervalEnd: '2026-07-01T12:10:00+10:00' })] }
      )
    );
    expect(html).toContain('Not comparable');
    expect(html).toContain('would invert the sign and display loss as outperformance');
  });

  it('reports AEMO re-runs as a reason the revenue figure moves', () => {
    const html = render(ready([{ ...row, priceSourceRunNo: 3 }, ...twoIntervals.slice(1)], { fuelRows: [fuel()] }));
    expect(html).toContain('re-run by AEMO since first publication');
    expect(html).toContain('Revenue on restated intervals');
  });

  it('says so plainly when no interval has been restated', () => {
    const html = render(ready(twoIntervals, { fuelRows: [fuel()] }));
    expect(html).toContain('Every interval shown is an original AEMO run');
  });

  it('keeps a charging battery visible as a distinct fuel with negative energy', () => {
    const html = render(
      ready(twoIntervals, {
        fuelRows: [
          fuel({ fuelType: 'Battery', actualGenerationMw: -600, intervalEnd: '2026-07-01T12:05:00+10:00' }),
          fuel({ fuelType: 'Battery', actualGenerationMw: 600, intervalEnd: '2026-07-01T12:10:00+10:00' }),
        ],
      })
    );
    expect(html).toContain('Battery charging');
    expect(html).toContain('Battery discharging');
    expect(html).toContain('−50 MWh');
  });

  it('surfaces stale source and prediction-stale states', () => {
    expect(render(ready(twoIntervals, { stale: true, fuelRows: [fuel()] }))).toContain('Stale source');
    expect(render(ready(twoIntervals, { predictionStale: true, fuelRows: [fuel()] }))).toContain(
      'Prediction inputs stale'
    );
    expect(render(ready(twoIntervals, { mode: 'mock', fuelRows: [fuel()] }))).toContain('Prepared non-live fixture');
  });

  it('alarms on staleness in integration mode but not against a prepared fixture', () => {
    const integration = render(ready(twoIntervals, { stale: true, fuelRows: [fuel()] }));
    const prepared = render(ready(twoIntervals, { stale: true, mode: 'mock', fuelRows: [fuel()] }));

    // Class names changed from state-banner-* to notice-* when the three stacked
    // full-width banners became one row of inline chips. The assertions are
    // unchanged in substance: live staleness alarms, prepared staleness does not.
    expect(integration).toContain('notice-alert');
    expect(integration).toContain('role="alert"');
    expect(prepared).toContain('notice-muted');
    expect(prepared).toContain('as expected for a prepared fixture');
    expect(prepared).not.toContain('notice-alert');
    // The safety instruction itself must survive the change of emphasis.
    for (const html of [integration, prepared]) {
      expect(html).toContain('Do not treat these values as current');
    }
  });

  it('preserves negative prices in the underlying observation table', () => {
    const html = render(
      ready([{ ...row, rrpAudPerMwh: -12.5, priceSourceRunNo: 1 }, twoIntervals[1]], { fuelRows: [fuel()] })
    );
    expect(html).toContain('−A$12.50/MWh');
  });

  it('labels repeated market-wide source-sign flow without regional direction', () => {
    const html = render(ready(twoIntervals, { fuelRows: [fuel()] }));
    expect(html).toContain('market-wide count');
    expect(html).toContain('AEMO source sign');
    expect(html).toContain('No regional allocation or directional interpretation');
  });

  it('does not rely on colour alone to show over- or under-capture', () => {
    // WCAG 1.4.1: the red/green rate colour is reinforced with a direction symbol
    // and a screen-reader label.
    const html = render(
      ready(twoIntervals, {
        fuelRows: [
          fuel({ fuelType: 'Solar', actualGenerationMw: 900, intervalEnd: '2026-07-01T12:05:00+10:00' }),
          fuel({ fuelType: 'Gas', actualGenerationMw: 900, intervalEnd: '2026-07-01T12:10:00+10:00' }),
        ],
      })
    );
    expect(html).toContain('below baseline');
    expect(html).toContain('at or above baseline');
    expect(html).toContain('▼');
    expect(html).toContain('▲');
  });

  it('offers the investigation journal for the focused interval', () => {
    const html = render(ready(twoIntervals, { fuelRows: [fuel()] }));
    expect(html).toContain('Investigate with Genie');
    expect(html).toContain('Investigate the observation with Genie');
  });
});
