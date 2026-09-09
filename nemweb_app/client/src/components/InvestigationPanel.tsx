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
  const [analysisShown, setAnalysisShown] = useState(false);
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
        <CardTitle>Investigate this observation</CardTitle>
        <CardDescription>
          Ask for a prepared analysis of {row.regionId} at {formatMarketTime(row.intervalEnd)}, then edit and save the
          follow-up note. This is snapshot evidence, not a live market recommendation.
        </CardDescription>
      </CardHeader>
      <form onSubmit={(event) => void submit(event)}>
        <CardContent className="investigation-form">
          <Button type="button" variant="outline" onClick={() => {
            setAnalysisShown(true);
            setDecision(
              `Prepared analysis for ${row.regionId}: review the observed price and generation evidence for this interval. ` +
                'The data does not establish availability, curtailment, causation, or a bid recommendation. Follow up by checking the corrected source record and freshness.'
            );
          }}>
            {analysisShown ? 'Refresh prepared analysis' : 'Ask Genie for a prepared analysis'}
          </Button>
          {analysisShown && (
            <Alert>
              <AlertDescription>
                Prepared Genie-style analysis: the selected interval is suitable for investigation, but this evidence
                does not establish availability, curtailment, causation, or a trading recommendation.
              </AlertDescription>
            </Alert>
          )}
          <Label htmlFor="decision">Investigation note</Label>
          <Textarea
            id="decision"
            value={decision}
            onChange={(event) => setDecision(event.target.value)}
            placeholder="Review the analysis, record what the evidence shows, and note any follow-up…"
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
          <p>Save the reviewed investigation to app-owned Lakebase state; the synced analytics source remains read-only.</p>
          <Button type="submit" disabled={saving || decision.trim().length === 0}>
            {saving ? 'Saving…' : 'Save investigation'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
