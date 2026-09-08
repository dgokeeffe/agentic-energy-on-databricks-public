import {
  Alert,
  AlertDescription,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Label,
  Textarea,
} from '@databricks/appkit-ui/react';
import { useState } from 'react';
import type { RegionStatus } from '../domain/regionStatus';
import { formatMarketTime } from '../domain/time';

export function InvestigationPanel({ row }: { row: RegionStatus }) {
  const [decision, setDecision] = useState('');
  const [status, setStatus] = useState('');
  const saving = status === 'Saving…';

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
    <Card className="investigation-card">
      <CardHeader>
        <CardTitle>Investigation journal</CardTitle>
        <CardDescription>
          Record an analyst decision against {row.regionId} at {formatMarketTime(row.intervalEnd)}. Identity is supplied
          by the trusted AppKit request context, never by this form.
        </CardDescription>
      </CardHeader>
      <form onSubmit={(event) => void submit(event)}>
        <CardContent className="investigation-form">
          <Label htmlFor="decision">Decision</Label>
          <Textarea
            id="decision"
            value={decision}
            onChange={(event) => setDecision(event.target.value)}
            placeholder="Record the observation, decision, and follow-up owner…"
            required
            rows={5}
          />
          {status && status !== 'Saving…' && (
            <Alert variant={status === 'Investigation saved.' ? 'default' : 'destructive'}>
              <AlertDescription>{status}</AlertDescription>
            </Alert>
          )}
        </CardContent>
        <CardFooter className="investigation-footer">
          <p>Writes only to app-owned Lakebase state; the synced analytics source remains read-only.</p>
          <Button type="submit" disabled={saving || decision.trim().length === 0}>
            {saving ? 'Saving…' : 'Record investigation'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
