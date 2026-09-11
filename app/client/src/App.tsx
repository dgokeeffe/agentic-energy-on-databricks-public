import { useEffect, useState } from 'react';
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

function usePanel(path: string) {
  const [result, setResult] = useState<{ loading: boolean; data?: unknown; error?: string }>({ loading: true });
  useEffect(() => {
    const controller = new AbortController();
    fetch(path, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('This data panel is temporarily unavailable.');
        return response.json() as Promise<unknown>;
      })
      .then((data) => setResult({ loading: false, data }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setResult({ loading: false, error: error instanceof Error ? error.message : 'Read failed' });
        }
      });
    return () => controller.abort();
  }, [path]);
  return result;
}

function IntegrationApp() {
  const query = usePanel('/api/region-status');
  const fuelQuery = usePanel('/api/fuel-generation');
  const unitQuery = usePanel('/api/unit-dispatch');
  if (query.loading) return <RegionalOperationsShell state={{ kind: 'loading' }} />;
  if (query.error) return <RegionalOperationsShell state={{ kind: 'error', message: query.error }} />;
  const fuelRows: FuelGenerationRow[] | null = fuelQuery.error ? null : fuelGenerationRowsOrNull(fuelQuery.data);
  const unitRows: UnitDispatchRow[] | null = unitQuery.error ? null : unitDispatchRowsOrNull(unitQuery.data);
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
