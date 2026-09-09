const DEFAULT_REGION_STATUS_TABLE =
  'agentic_energy_workshop.agentic_energy_workshop_d4_serving.gold_nem_app_region_status';
const DEFAULT_FUEL_GENERATION_TABLE =
  'agentic_energy_workshop.agentic_energy_workshop_d4_serving.gold_nem_scada_generation_5min';
const QUALIFIED_TABLE = /^[A-Za-z_][A-Za-z0-9_-]*\.[A-Za-z_][A-Za-z0-9_-]*\.[A-Za-z_][A-Za-z0-9_]*$/;

function reviewedTable(value: string | undefined, expectedTable: string, fallback: string): string {
  const candidate = value || fallback;
  if (!QUALIFIED_TABLE.test(candidate) || candidate.split('.')[2] !== expectedTable) {
    throw new Error(`Invalid reviewed serving-table identifier for ${expectedTable}`);
  }
  return candidate;
}

function environmentString(name: string): string | undefined {
  const value: unknown = import.meta.env[name];
  return typeof value === 'string' ? value : undefined;
}

export const servingTableParameters = Object.freeze({
  region_status_table: reviewedTable(
    environmentString('VITE_REGION_STATUS_TABLE'),
    'gold_nem_app_region_status',
    DEFAULT_REGION_STATUS_TABLE
  ),
  fuel_generation_table: reviewedTable(
    environmentString('VITE_FUEL_GENERATION_TABLE'),
    'gold_nem_scada_generation_5min',
    DEFAULT_FUEL_GENERATION_TABLE
  ),
});
