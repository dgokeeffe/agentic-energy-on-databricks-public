import {
  Alert,
  AlertDescription,
  AlertTitle,
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
  Skeleton,
} from '@databricks/appkit-ui/react';
import { CircleAlert, Database } from 'lucide-react';

export function QueryStateMessage({ kind, message }: { kind: 'loading' | 'empty' | 'error'; message?: string }) {
  if (kind === 'loading') {
    return (
      <main className="query-state-shell" role="status" aria-label="Loading regional conditions">
        <div className="query-state-heading">
          <Skeleton className="skeleton-line skeleton-short" />
          <Skeleton className="skeleton-line skeleton-title" />
          <Skeleton className="skeleton-line" />
        </div>
        <div className="query-state-grid">
          {[0, 1, 2, 3].map((item) => (
            <Skeleton className="skeleton-card" key={item} />
          ))}
        </div>
        <span className="sr-only">Loading regional conditions…</span>
      </main>
    );
  }

  if (kind === 'empty') {
    return (
      <main className="query-state-shell query-state-centred">
        <Empty>
          <Database aria-hidden="true" />
          <EmptyHeader>
            <EmptyTitle>No regional conditions are available</EmptyTitle>
            <EmptyDescription>
              The governed query returned no effective-run rows. Check publication status before making an operator
              decision.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </main>
    );
  }

  return (
    <main className="query-state-shell query-state-centred">
      <Alert variant="destructive" className="query-error">
        <CircleAlert aria-hidden="true" />
        <AlertTitle>Regional conditions could not be loaded</AlertTitle>
        <AlertDescription>{message ?? 'Unknown error'}</AlertDescription>
      </Alert>
    </main>
  );
}
