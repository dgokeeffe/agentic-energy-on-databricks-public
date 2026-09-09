import { describe, expect, it } from 'vitest';
import { servingTableParameters } from './servingTables';

describe('serving table configuration', () => {
  it('keeps the two reviewed development-compatible table contracts', () => {
    expect(servingTableParameters.region_status_table).toMatch(/\.gold_nem_app_region_status$/);
    expect(servingTableParameters.fuel_generation_table).toMatch(/\.gold_nem_scada_generation_5min$/);
    expect(Object.keys(servingTableParameters)).toEqual([
      'region_status_table',
      'fuel_generation_table',
    ]);
  });
});
