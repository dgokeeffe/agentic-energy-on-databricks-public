import fixture from '../../../tests/fixtures/fuel-generation.json';
import type { FuelGenerationRepository } from './fuelGenerationRepository';
import type { FuelGenerationRow } from '../domain/fuelCapture';

export class MockFuelGenerationRepository implements FuelGenerationRepository {
  load(): Promise<FuelGenerationRow[]> {
    return Promise.resolve(structuredClone(fixture) as FuelGenerationRow[]);
  }
}
