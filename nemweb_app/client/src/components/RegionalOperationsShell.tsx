import type { QueryState } from '../domain/regionStatus';
import { InvestigationPanel } from './InvestigationPanel';
import { QueryStateMessage } from './QueryState';
import { SourceFreshness } from './SourceFreshness';

export function RegionalOperationsShell({ state }: { state: QueryState }) {
  if (state.kind === 'loading') return <QueryStateMessage kind="loading" />;
  if (state.kind === 'empty') return <QueryStateMessage kind="empty" />;
  if (state.kind === 'error') return <QueryStateMessage kind="error" message={state.message} />;

  const first = state.rows[0];
  if (!first) return <QueryStateMessage kind="empty" />;

  return (
    <main>
      <header>
        <p>{state.mode === 'mock' ? 'Prepared non-live fixture' : 'Databricks Analytics integration'}</p>
        <h1>Current NEM regional conditions</h1>
        <p>Five-minute interval-ending AEST market data; intervention effective run only.</p>
      </header>

      {state.stale && <p role="alert">Stale source: do not treat these values as current.</p>}
      {state.partial && <p role="status">Partial result: prediction fields are not available.</p>}

      <table>
        <caption>Regional dispatch price and demand</caption>
        <thead>
          <tr>
            <th>Region</th>
            <th>Interval end</th>
            <th>Dispatch price (AUD/MWh)</th>
            <th>Demand (MW)</th>
          </tr>
        </thead>
        <tbody>
          {state.rows.map((row) => (
            <tr key={`${row.regionId}|${row.intervalEnd}`}>
              <th>{row.regionId}</th>
              <td>{row.intervalEnd}</td>
              <td>{row.rrpAudPerMwh.toFixed(2)}</td>
              <td>{row.totalDemandMw.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <section aria-labelledby="market-wide-heading">
        <h2 id="market-wide-heading">Market-wide context</h2>
        <p>Binding constraints (market-wide): {first.marketWideBindingConstraintCount}</p>
        <p>Interconnectors (market-wide): {first.marketWideInterconnectorCount}</p>
        <p>Interconnector flow (market-wide, AEMO source sign, MW): {first.marketWideInterconnectorSourceSignFlowMw}</p>
        <p>
          No regional allocation or directional interpretation is inferred because no governed interconnector-to-region
          mapping is available.
        </p>
      </section>

      <SourceFreshness row={first} />
      <InvestigationPanel row={first} />
    </main>
  );
}
