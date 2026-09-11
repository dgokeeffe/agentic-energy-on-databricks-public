const MARKET_TIME_ZONE = 'Australia/Brisbane';

function parseTimestamp(value: string) {
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? null : timestamp;
}

export function formatMarketTime(value: string) {
  const timestamp = parseTimestamp(value);
  if (timestamp === null) return 'Unavailable';
  return new Intl.DateTimeFormat('en-AU', {
    timeZone: MARKET_TIME_ZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZoneName: 'short',
  }).format(timestamp);
}

export function formatUtc(value: string) {
  const timestamp = parseTimestamp(value);
  if (timestamp === null) return 'Unavailable';
  return `${new Intl.DateTimeFormat('en-AU', {
    timeZone: 'UTC',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(timestamp)} UTC`;
}

export function formatDuration(seconds: number) {
  const sign = seconds < 0 ? '−' : '';
  const absolute = Math.abs(seconds);
  if (absolute < 60) return `${sign}${absolute}s`;
  if (absolute < 3600) return `${sign}${Math.round(absolute / 60)}m`;
  if (absolute < 86400) return `${sign}${(absolute / 3600).toFixed(1)}h`;
  return `${sign}${(absolute / 86400).toFixed(1)}d`;
}
