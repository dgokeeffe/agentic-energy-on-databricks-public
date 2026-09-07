import fixture from '../../../tests/fixtures/region-status.json';
import type { RegionStatusRepository } from './regionStatusRepository';
import type { RegionStatus } from '../domain/regionStatus';

export class MockRegionStatusRepository implements RegionStatusRepository {
  load(): Promise<RegionStatus[]> {
    return Promise.resolve(structuredClone(fixture) as RegionStatus[]);
  }
}
