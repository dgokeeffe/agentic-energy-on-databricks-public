import fixture from '../../../tests/fixtures/unit-dispatch.json';
import type { UnitDispatchRepository } from './unitDispatchRepository';
import type { UnitDispatchRow } from '../domain/facilityMap';

/**
 * Prepared per-unit output for local work and tests.
 *
 * The DUIDs are real and resolve against the facility coordinate reference, so
 * the mock map has the same shape as the governed one. The fixture deliberately
 * includes an unmatched DUID (`NOCOORD1`) and two trailing intervals so the
 * coverage reporting and latest-interval reduction are exercised offline.
 */
export class MockUnitDispatchRepository implements UnitDispatchRepository {
  load(): Promise<UnitDispatchRow[]> {
    return Promise.resolve(structuredClone(fixture) as UnitDispatchRow[]);
  }
}
