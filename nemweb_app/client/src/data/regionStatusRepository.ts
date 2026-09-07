import type { RegionStatus } from '../domain/regionStatus';

export interface RegionStatusRepository {
  load(): Promise<RegionStatus[]>;
}
