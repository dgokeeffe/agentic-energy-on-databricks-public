import type { RegionStatus } from '../domain/regionStatus';

export function SourceFreshness({ row }: { row: RegionStatus }) {
  return (
    <dl>
      <div>
        <dt>Source interval</dt>
        <dd>{row.sourceIntervalWatermark}</dd>
      </div>
      <div>
        <dt>NEMWEB publication</dt>
        <dd>{row.sourcePublicationAt}</dd>
      </div>
      <div>
        <dt>Gold publication</dt>
        <dd>{row.goldPublishedAt}</dd>
      </div>
    </dl>
  );
}
