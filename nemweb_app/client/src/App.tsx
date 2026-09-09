import { useEffect, useState } from 'react';
import { useAnalyticsQuery } from '@databricks/appkit-ui/react';
import { RegionalOperationsShell } from './components/RegionalOperationsShell';
import { classifyRows, type QueryState } from './domain/regionStatus';
import type { FuelGenerationRow } from './domain/fuelCapture';
import { integrationQueryState } from './data/integrationRegionStatusRepository';
import { fuelGenerationRowsOrNull } from './data/fuelGenerationRepository';
import { MockRegionStatusRepository } from './data/mockRegionStatusRepository';
import { MockFuelGenerationRepository } from './data/mockFuelGenerationRepository';

function MockApp() {
  const [state, setState] = useState<QueryState>({ kind: 'loading' });
  useEffect(() => {
    Promise.all([new MockRegionStatusRepository().load(), new MockFuelGenerationRepository().load()])
      // Inside an effect, so evaluating the instant here is not a render-time call.
      .then(([rows, fuelRows]) => setState(classifyRows(rows, 'mock', Date.now(), fuelRows)))
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
  const query = useAnalyticsQuery('latest_region_status', EMPTY_QUERY_PARAMETERS);
  // Separate governed read. Its failure must not blank the page: the generation
  // tables need a Unity Catalog grant the region-status table does not imply, so
  // an unprivileged deployment still has to report price and freshness.
  const fuelQuery = useAnalyticsQuery('latest_fuel_generation', EMPTY_QUERY_PARAMETERS);

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
  return <RegionalOperationsShell state={integrationQueryState(query.data, fuelRows)} />;
}

export default function App() {
  return import.meta.env.VITE_DATA_MODE === 'mock' ? <MockApp /> : <IntegrationApp />;
}
