import { describe, expect, it } from 'vitest';
import { fuelGenerationRowsOrNull, normaliseFuelGenerationRows } from './fuelGenerationRepository';
import { registrationAttribution } from '../domain/fuelCapture';

/**
 * The exact eleven columns of the serving table as deployed on 2026-09-10, read
 * from `system.information_schema.columns` in the workspace rather than assumed.
 *
 * It carries **no** `registration_*` columns: the attribution columns exist in the
 * pipeline source but have not reached the serving surface, because publishing
 * them requires the foundation pipeline and the serving job to run.
 *
 * That makes this the shape the app will actually meet between merging this change
 * and the next authorised deployment. A read that threw here, or that reported
 * freshness it had no evidence for, would be a live defect during exactly that
 * window.
 */
const DEPLOYED_SERVING_ROW = {
  interval_end: '2026-07-01T12:05:00+10:00',
  region_id: 'NSW1',
  fuel_type: 'Black coal',
  actual_generation_mw: 1200,
  facility_count: 4,
  partially_enriched_facility_count: 2,
  source_publication_at: '2026-07-01T02:06:00Z',
  silver_published_at: '2026-07-01T02:06:30Z',
  source_interval_watermark: '2026-07-01T12:05:00+10:00',
  gold_published_at: '2026-07-01T02:07:00Z',
  source_mode: 'snapshot',
};

describe('fuel generation read against the deployed serving schema', () => {
  it('parses a row that predates the attribution columns', () => {
    const rows = fuelGenerationRowsOrNull([DEPLOYED_SERVING_ROW]);
    expect(rows).not.toBeNull();
    expect(rows![0].actualGenerationMw).toBe(1200);
    // The count that this change renders for the first time must survive the
    // older schema, since it is one of the columns that does already exist.
    expect(rows![0].partiallyEnrichedFacilityCount).toBe(2);
  });

  it('reports not assessable rather than false freshness when the columns are absent', () => {
    // Absent must not become zero. Zero coverage would render "attribution is
    // current" from a table that carries no attribution evidence at all.
    const attribution = registrationAttribution(fuelGenerationRowsOrNull([DEPLOYED_SERVING_ROW])!);
    expect(attribution.assessable).toBe(false);
    expect(attribution.coverageSeconds).toBeNull();
    expect(attribution.stale).toBe(false);
  });

  it('reads the attribution columns once the serving table has them', () => {
    const rows = normaliseFuelGenerationRows([
      {
        ...DEPLOYED_SERVING_ROW,
        registration_effective_at: '2026-07-01T12:10:00+10:00',
        registration_publication_at: '2026-06-30T02:00:00Z',
        registration_coverage_seconds: 93600,
        registration_coverage_basis: 'LISTING_OR_HTTP',
      },
    ]);
    expect(rows[0].registrationCoverageSeconds).toBe(93600);
    expect(registrationAttribution(rows).assessable).toBe(true);
  });

  it('keeps an explicit null distinct from a missing column', () => {
    // The pipeline publishes NULL when either publication instant is absent, which
    // is a different fact from the column not existing — but both must fail closed.
    const rows = normaliseFuelGenerationRows([
      {
        ...DEPLOYED_SERVING_ROW,
        registration_effective_at: null,
        registration_publication_at: null,
        registration_coverage_seconds: null,
        registration_coverage_basis: 'UNKNOWN',
      },
    ]);
    expect(rows[0].registrationCoverageSeconds).toBeNull();
    expect(registrationAttribution(rows).assessable).toBe(false);
  });
});
