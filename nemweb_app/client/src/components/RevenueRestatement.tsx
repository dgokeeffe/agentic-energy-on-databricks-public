import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@databricks/appkit-ui/react';
import { formatAud, type RegionCapture } from '../domain/fuelCapture';
import { formatUtc } from '../domain/time';

/**
 * Why the revenue figure is allowed to move.
 *
 * This is the point where the governed provenance work becomes commercial: when
 * AEMO re-runs a dispatch interval the price changes, so revenue already
 * reported changes with it. Stating the restated interval count and the affected
 * value is the difference between "the data is trustworthy" and "here is the
 * figure that moved, and why".
 */
export function RevenueRestatement({
  capture,
  goldPublishedAt,
  restatedRevenueAud,
}: {
  capture: RegionCapture;
  goldPublishedAt: string;
  restatedRevenueAud: number;
}) {
  const restated = capture.restatedIntervalCount > 0;

  return (
    <Card id="restatement" className="restatement-card">
      <CardHeader>
        <p className="section-kicker">Why the number can move</p>
        <CardTitle>
          <h2 className="section-title">
            {restated
              ? `${capture.restatedIntervalCount} interval${capture.restatedIntervalCount === 1 ? '' : 's'} re-run by AEMO since first publication`
              : 'Every interval shown is an original AEMO run'}
          </h2>
        </CardTitle>
        <CardDescription>
          {restated
            ? 'A re-run changes the dispatch price, so revenue already reported for those intervals changes with it. Only the effective run is counted here, which is why the figure differs from a naive sum over all runs.'
            : 'No price in this window has been restated. If AEMO re-runs one, the revenue above changes and this card reports by how much.'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="restatement-figures">
          <div>
            <dt>Restated intervals</dt>
            <dd>
              {capture.restatedIntervalCount} of {capture.intervalCount}
            </dd>
          </div>
          <div>
            <dt>Revenue on restated intervals</dt>
            <dd>{formatAud(restatedRevenueAud)}</dd>
          </div>
          <div>
            <dt>Negative-price intervals</dt>
            <dd>
              {capture.negativePriceIntervalCount} of {capture.intervalCount}
            </dd>
          </div>
          <div>
            <dt>Gold published</dt>
            <dd>{formatUtc(goldPublishedAt)}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
