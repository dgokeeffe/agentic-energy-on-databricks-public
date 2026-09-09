import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle } from '@databricks/appkit-ui/react';
import type { RegionStatus } from '../domain/regionStatus';
import { formatMarketTime, formatUtc } from '../domain/time';

export function SourceFreshness({ row, stale }: { row: RegionStatus; stale: boolean }) {
  return (
    <Card>
      <CardHeader className="freshness-header">
        <div>
          <CardTitle>
            <h2 className="section-title">Source and freshness · {row.regionId}</h2>
          </CardTitle>
          <CardDescription>Market interval in fixed AEST; publication and processing times in UTC.</CardDescription>
        </div>
        <Badge variant={stale ? 'destructive' : 'secondary'}>{stale ? 'Stale' : 'Available'}</Badge>
      </CardHeader>
      <CardContent>
        <dl className="freshness-list">
          <div>
            <dt>Source interval</dt>
            <dd>{formatMarketTime(row.sourceIntervalWatermark)}</dd>
          </div>
          <div>
            <dt>NEMWEB publication</dt>
            <dd>{formatUtc(row.sourcePublicationAt)}</dd>
          </div>
          <div>
            <dt>Gold publication</dt>
            <dd>{formatUtc(row.goldPublishedAt)}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
