export function QueryStateMessage({ kind, message }: { kind: 'loading' | 'empty' | 'error'; message?: string }) {
  if (kind === 'loading') return <p role="status">Loading regional conditions…</p>;
  if (kind === 'empty') return <p role="status">No regional conditions are available.</p>;
  return <p role="alert">Regional conditions could not be loaded: {message ?? 'Unknown error'}</p>;
}
