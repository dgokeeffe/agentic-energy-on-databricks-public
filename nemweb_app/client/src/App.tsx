import { useEffect, useMemo, useState } from 'react';
import { useAnalyticsQuery } from '@databricks/appkit-ui/react';
import { sql } from '@databricks/appkit-ui/js';
import { RegionalOperationsShell } from './components/RegionalOperationsShell';
import { classifyRows, type QueryState } from './domain/regionStatus';
import type { FuelGenerationRow } from './domain/fuelCapture';
import type { UnitDispatchRow } from './domain/facilityMap';
import { integrationQueryState } from './data/integrationRegionStatusRepository';
import { fuelGenerationRowsOrNull } from './data/fuelGenerationRepository';
import { unitDispatchRowsOrNull } from './data/unitDispatchRepository';
import { MockRegionStatusRepository } from './data/mockRegionStatusRepository';
import { MockFuelGenerationRepository } from './data/mockFuelGenerationRepository';
import { MockUnitDispatchRepository } from './data/mockUnitDispatchRepository';
import { applyTheme, preferredTheme } from './lib/theme';
import { servingTableParameters } from './config/servingTables';

function MockApp() {
  const [state, setState] = useState<QueryState>({ kind: 'loading' });
  useEffect(() => {
    Promise.all([
      new MockRegionStatusRepository().load(),
      new MockFuelGenerationRepository().load(),
      new MockUnitDispatchRepository().load(),
    ])
      // Inside an effect, so evaluating the instant here is not a render-time call.
      .then(([rows, fuelRows, unitRows]) =>
        setState(classifyRows(rows, 'mock', Date.now(), fuelRows, unitRows))
      )
      .catch((error: unknown) =>
        setState({
          kind: 'error',
          message: error instanceof Error ? error.message : 'Prepared fixture failed',
        })
      );
  }, []);
  return <RegionalOperationsShell state={state} />;
}

const EMPTY_QUERY_PARAMETERS: Record<string, never> = Object.freeze({});

function IntegrationApp() {
  const regionParameters = useMemo(() => ({
    region_status_table: sql.string(servingTableParameters.region_status_table),
  }), []);
  const fuelParameters = useMemo(() => ({
    fuel_generation_table: sql.string(servingTableParameters.fuel_generation_table),
  }), []);
  const query = useAnalyticsQuery('latest_region_status', regionParameters);
  // Separate governed read. Its failure must not blank the page: the generation
  // tables need a Unity Catalog grant the region-status table does not imply, so
  // an unprivileged deployment still has to report price and freshness.
  const fuelQuery = useAnalyticsQuery('latest_fuel_generation', fuelParameters);
  // Third governed read, on the same principle: the generator map needs SELECT on
  // the per-unit table, which neither of the other two grants implies. Losing it
  // costs the map alone.
  const unitQuery = useAnalyticsQuery('latest_unit_dispatch', EMPTY_QUERY_PARAMETERS);

  if (query.warehouseStatus && query.warehouseStatus.state !== 'RUNNING') {
    return (
      <RegionalOperationsShell
        state={{ kind: 'error', message: `Warehouse is ${query.warehouseStatus.state.toLowerCase()}…` }}
      />
    );
  }
  if (query.loading) return <RegionalOperationsShell state={{ kind: 'loading' }} />;
  if (query.error) {
    return <RegionalOperationsShell state={{ kind: 'error', message: String(query.error) }} />;
  }

  const fuelRows: FuelGenerationRow[] | null =
    fuelQuery.loading || fuelQuery.error ? null : fuelGenerationRowsOrNull(fuelQuery.data);
  const unitRows: UnitDispatchRow[] | null =
    unitQuery.loading || unitQuery.error ? null : unitDispatchRowsOrNull(unitQuery.data);
  return <RegionalOperationsShell state={integrationQueryState(query.data, fuelRows, unitRows)} />;
}

export default function App() {
  // Set once on mount rather than in index.html, so the stored preference and the
  // operating-system fallback are resolved in one place. index.html still ships
  // class="light" so the first paint is never AppKit's dark fallback.
  useEffect(() => {
    applyTheme(preferredTheme());
  }, []);

  return import.meta.env.VITE_DATA_MODE === 'mock' ? <MockApp /> : <IntegrationApp />;
}
