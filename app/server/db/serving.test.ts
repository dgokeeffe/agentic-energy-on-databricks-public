import { describe, expect, it } from 'vitest';
import { servingQueries } from './serving';
import { normaliseIntegrationRows } from '../../client/src/data/integrationRegionStatusRepository';
import { normaliseFuelGenerationRows } from '../../client/src/data/fuelGenerationRepository';
import { normaliseUnitDispatchRows } from '../../client/src/data/unitDispatchRepository';
import regions from '../../client/src/data/fixtures/region-status.json';
import fuels from '../../client/src/data/fixtures/fuel-generation.json';
import units from '../../client/src/data/fixtures/unit-dispatch.json';

function apiProjection(query: string, domain: object): Record<string, unknown> {
  const row = Object.fromEntries(Object.entries(domain).map(([key, value]) => [
    key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`), value,
  ]));
  const columns = query.split('SELECT ')[1].split('FROM ')[0].split(',').map((c) => c.trim());
  return Object.fromEntries(columns.map((column) => [column, row[column]]));
}

describe('Lakebase API/client contracts', () => {
  it('projects every required regional field, including both source runs', () => {
    const source = regions[0];
    expect(normaliseIntegrationRows([apiProjection(servingQueries['/api/region-status'], source)]))
      .toEqual([source]);
  });
  it('projects fuel coverage and unit map fields without warehouse bindings', () => {
    expect(normaliseFuelGenerationRows([apiProjection(servingQueries['/api/fuel-generation'], fuels[0])]))
      .toHaveLength(1);
    expect(normaliseUnitDispatchRows([apiProjection(servingQueries['/api/unit-dispatch'], units[0])]))
      .toHaveLength(1);
  });
});
