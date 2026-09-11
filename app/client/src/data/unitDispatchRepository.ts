import { z } from 'zod';
import type { UnitDispatchRow } from '../domain/facilityMap';

/**
 * Read path for five-minute per-DUID output, used by the generator map.
 *
 * A third repository rather than an extension of either existing one: unit
 * dispatch is a different governed Gold surface at a different grain (per DUID,
 * not per region and fuel), needing its own reviewed SQL and its own Unity
 * Catalog grant. Folding it into an existing contract would hide that third
 * privilege behind a privilege already granted.
 */
export interface UnitDispatchRepository {
  load(): Promise<UnitDispatchRow[]>;
}

const requiredNumber = z.preprocess(
  (value) => (typeof value === 'string' && value.trim() !== '' ? Number(value) : value),
  z.number().finite()
);
const optionalNumber = z.preprocess(
  (value) => (typeof value === 'string' && value.trim() !== '' ? Number(value) : value),
  z.number().finite().nullable()
);
const timestamp = z.iso.datetime({ offset: true });

const unitDispatchRowSchema = z.object({
  interval_end: timestamp,
  duid: z.string().min(1),
  actual_generation_mw: requiredNumber,
  region_id: z.string().min(1),
  fuel_type: z.string().min(1),
  registered_capacity_mw: optionalNumber,
  dimension_match_status: z.string().min(1),
});

export function normaliseUnitDispatchRows(rows: unknown[]): UnitDispatchRow[] {
  return rows.map((candidate) => {
    const row = unitDispatchRowSchema.parse(candidate);
    return {
      intervalEnd: row.interval_end,
      duid: row.duid,
      actualGenerationMw: row.actual_generation_mw,
      regionId: row.region_id,
      fuelType: row.fuel_type,
      registeredCapacityMw: row.registered_capacity_mw,
      dimensionMatchStatus: row.dimension_match_status,
    };
  });
}

/**
 * Parse an API payload into unit rows, or return null.
 *
 * Null rather than an error state, matching `fuelGenerationRowsOrNull`: the map
 * is one section of the journey, so an unprivileged deployment must lose that
 * section rather than blank the page and take governed price and freshness
 * reporting down with it.
 */
export function unitDispatchRowsOrNull(data: unknown): UnitDispatchRow[] | null {
  try {
    if (!Array.isArray(data)) return null;
    return normaliseUnitDispatchRows(data);
  } catch {
    return null;
  }
}

export class IntegrationUnitDispatchRepository implements UnitDispatchRepository {
  private readonly loader: () => Promise<unknown[]>;

  constructor(loader: () => Promise<unknown[]>) {
    this.loader = loader;
  }

  async load(): Promise<UnitDispatchRow[]> {
    return normaliseUnitDispatchRows(await this.loader());
  }
}
