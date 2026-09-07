import { useState } from 'react';
import type { RegionStatus } from '../domain/regionStatus';

export function InvestigationPanel({ row }: { row: RegionStatus }) {
  const [decision, setDecision] = useState('');
  const [status, setStatus] = useState('');

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setStatus('Saving…');
    try {
      const response = await fetch('/api/investigations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nemEventKey: `${row.regionId}|${row.intervalEnd}`,
          regionId: row.regionId,
          intervalEnd: row.intervalEnd,
          teamIdentifier: 'workshop-pair',
          status: 'open',
          decision,
        }),
      });
      setStatus(response.ok ? 'Investigation saved.' : 'Investigation could not be saved.');
    } catch {
      setStatus('Investigation could not be saved.');
    }
  }

  return (
    <section aria-labelledby="investigation-heading">
      <h2 id="investigation-heading">Investigation journal</h2>
      <p>Operator identity is supplied by the trusted AppKit request context, not this form.</p>
      <form onSubmit={(event) => void submit(event)}>
        <label htmlFor="decision">Decision</label>
        <textarea id="decision" value={decision} onChange={(event) => setDecision(event.target.value)} required />
        <button type="submit">Record investigation</button>
      </form>
      {status && <p role="status">{status}</p>}
    </section>
  );
}
