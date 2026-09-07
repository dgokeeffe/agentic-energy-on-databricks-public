import { useEffect, useState } from 'react';
import { useAnalyticsQuery } from '@databricks/appkit-ui/react';
import { RegionalOperationsShell } from './components/RegionalOperationsShell';
import { classifyRows, type QueryState } from './domain/regionStatus';
import { normaliseIntegrationRows } from './data/integrationRegionStatusRepository';
import { MockRegionStatusRepository } from './data/mockRegionStatusRepository';

function MockApp() {
  const [state, setState] = useState<QueryState>({ kind: 'loading' });
  useEffect(() => {
    new MockRegionStatusRepository()
      .load()
      .then((rows) => setState(classifyRows(rows, 'mock')))
      .catch((error: unknown) =>
        setState({
          kind: 'error',
          message: error instanceof Error ? error.message : 'Prepared fixture failed',
        })
      );
  }, []);
  return <RegionalOperationsShell state={state} />;
}

function IntegrationApp() {
  const query = useAnalyticsQuery('latest_region_status', {});
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
  const candidates: unknown[] = Array.isArray(query.data) ? query.data : [];
  const rows = normaliseIntegrationRows(candidates);
  return <RegionalOperationsShell state={classifyRows(rows, 'integration')} />;
}

export default function App() {
  return import.meta.env.VITE_DATA_MODE === 'mock' ? <MockApp /> : <IntegrationApp />;
}
