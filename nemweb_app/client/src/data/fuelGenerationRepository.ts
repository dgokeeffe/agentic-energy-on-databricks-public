import { z } from 'zod';
import type { FuelGenerationRow } from '../domain/fuelCapture';

/**
 * Read path for five-minute generation by region and fuel.
 *
 * Deliberately separate from RegionStatusRepository: generation is a different
 * governed Gold surface at a different grain, and integration mode needs its own
 * reviewed SQL and its own Unity Catalog grant. Folding it into the region-status
 * contract would hide that second privilege behind an existing one.
 */
export interface FuelGenerationRepository {
  load(): Promise<FuelGenerationRow[]>;
}

const requiredNumber = z.preprocess(
  (value) => (typeof value === 'string' && value.trim() !== '' ? Number(value) : value),
  z.number().finite()
);
const timestamp = z.iso.datetime({ offset: true });

/**
 * Coverage columns are nullable, unlike every other field here.
 *
 * The pipeline publishes NULL rather than 0 when either publication instant is
 * absent, because zero would read as perfect coverage on a schema holding
 * nothing. Defaulting a missing value to 0 in this parser would undo that and
 * report the strongest possible freshness from the weakest possible evidence.
 * They are also optional, so a deployment whose serving table predates the new
 * columns degrades to "not assessable" rather than failing the whole read.
 */
const nullableNumber = z.preprocess(
  (value) => (typeof value === 'string' && value.trim() !== '' ? Number(value) : value),
  z.number().finite().nullable()
);

const fuelGenerationRowSchema = z.object({
  interval_end: timestamp,
  region_id: z.string().min(1),
  fuel_type: z.string().min(1),
  actual_generation_mw: requiredNumber,
  facility_count: requiredNumber,
  partially_enriched_facility_count: requiredNumber,
  registration_coverage_seconds: nullableNumber.optional(),
  registration_coverage_basis: z.string().min(1).nullable().optional(),
  registration_publication_at: timestamp.nullable().optional(),
});

export function normaliseFuelGenerationRows(rows: unknown[]): FuelGenerationRow[] {
  return rows.map((candidate) => {
    const row = fuelGenerationRowSchema.parse(candidate);
    return {
      intervalEnd: row.interval_end,
      regionId: row.region_id,
      fuelType: row.fuel_type,
      actualGenerationMw: row.actual_generation_mw,
      facilityCount: row.facility_count,
      partiallyEnrichedFacilityCount: row.partially_enriched_facility_count,
      registrationCoverageSeconds: row.registration_coverage_seconds ?? null,
      registrationCoverageBasis: row.registration_coverage_basis ?? null,
      registrationPublicationAt: row.registration_publication_at ?? null,
    };
  });
}

/**
 * Parse an analytics payload into fuel rows, or return null.
 *
 * Null rather than an error state: fuel capture is an enrichment of the screen,
 * so a failure here must degrade that one section rather than blank the page and
 * lose the governed price and freshness reporting alongside it.
 */
export function fuelGenerationRowsOrNull(data: unknown): FuelGenerationRow[] | null {
  try {
    if (!Array.isArray(data)) return null;
    return normaliseFuelGenerationRows(data);
  } catch {
    return null;
  }
}

export class IntegrationFuelGenerationRepository implements FuelGenerationRepository {
  private readonly loader: () => Promise<unknown[]>;

  constructor(loader: () => Promise<unknown[]>) {
    this.loader = loader;
  }

  async load(): Promise<FuelGenerationRow[]> {
    return normaliseFuelGenerationRows(await this.loader());
  }
}
