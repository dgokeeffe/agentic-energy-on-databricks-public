import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@databricks/appkit-ui/react';
import { ChartNoAxesCombined } from 'lucide-react';
import {
  formatAud,
  formatCaptureRate,
  formatMwh,
  formatPrice,
  type FuelCapture,
  type RegionCapture,
} from '../domain/fuelCapture';

/**
 * Widest capture rate the axis will show. Rates above this are clamped so one
 * exceptional battery interval cannot compress every other fuel to invisibility.
 */
const AXIS_MAX = 2;

function fuelColour(token: FuelCapture['token']) {
  return `var(--fuel-${token})`;
}

function CaptureRow({ fuel }: { fuel: FuelCapture }) {
  const rate = fuel.captureRate;
  const clamped = rate === null ? 0 : Math.max(0, Math.min(rate, AXIS_MAX));
  const widthPercent = (clamped / AXIS_MAX) * 100;
  const baselinePercent = (1 / AXIS_MAX) * 100;
  const rateClass = rate === null ? '' : rate >= 1 ? ' capture-rate-strong' : ' capture-rate-weak';
  // Colour alone must not carry the over/under-baseline meaning (WCAG 1.4.1), so
  // the rate is prefixed with a direction symbol that is also read aloud.
  const marker = rate === null ? '' : rate >= 1 ? '▲ ' : '▼ ';
  const markerLabel = rate === null ? '' : rate >= 1 ? 'at or above baseline' : 'below baseline';

  return (
    <li className="capture-row">
      <div className="capture-fuel">
        <span className="fuel-swatch" style={{ background: fuelColour(fuel.token) }} aria-hidden="true" />
        <span>
          <span className="capture-fuel-name">{fuel.label}</span>
          <span className="capture-fuel-volume">
            {formatMwh(fuel.energyMwh)} · {formatPrice(fuel.volumeWeightedPriceAudPerMwh)}
          </span>
        </span>
      </div>
      <div
        className="capture-track"
        role="img"
        aria-label={`${fuel.label} captured ${formatCaptureRate(rate)} of the regional average price`}
      >
        {rate !== null && (
          <span className="capture-fill" style={{ width: `${widthPercent}%`, background: fuelColour(fuel.token) }} />
        )}
        <span className="capture-baseline" style={{ left: `${baselinePercent}%` }} aria-hidden="true" />
      </div>
      <div className="capture-figures">
        <span className={`capture-rate${rateClass}`}>
          <span aria-hidden="true">{marker}</span>
          {formatCaptureRate(rate)}
          {markerLabel && <span className="sr-only"> {markerLabel}</span>}
        </span>
        <span className="capture-revenue">{formatAud(fuel.revenueAud)}</span>
        {fuel.negativePriceIntervalCount > 0 && (
          <span className={`capture-revenue${fuel.negativePriceCostAud < 0 ? ' capture-negative' : ''}`}>
            {formatAud(fuel.negativePriceCostAud)}{' '}
            {/* A net consumer earns money at a negative price, so the same field
                has to read as a benefit rather than always as a cost. */}
            {fuel.negativePriceCostAud < 0 ? 'lost' : 'earned'} over {fuel.negativePriceIntervalCount} negative interval
            {fuel.negativePriceIntervalCount === 1 ? '' : 's'}
          </span>
        )}
      </div>
    </li>
  );
}

export function FuelValueCapture({
  capture,
  regions,
  selectedRegion,
  onRegionChange,
}: {
  capture: RegionCapture | null;
  regions: string[];
  selectedRegion: string;
  onRegionChange: (region: string) => void;
}) {
  const regionSelect = (
    <div className="region-select">
      <label id="capture-region-label">Region</label>
      <Select value={selectedRegion} onValueChange={onRegionChange}>
        <SelectTrigger aria-labelledby="capture-region-label" size="sm">
          <SelectValue placeholder="Select a region" />
        </SelectTrigger>
        <SelectContent>
          {regions.map((region) => (
            <SelectItem key={region} value={region}>
              {region}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );

  if (!capture || capture.fuels.length === 0) {
    return (
      <Card id="value-capture" className="capture-card">
        <CardHeader className="capture-header">
          <div>
            <p className="section-kicker">Value capture</p>
            <CardTitle>
              <h2 className="section-title">No priced generation for {selectedRegion}</h2>
            </CardTitle>
          </div>
          {regionSelect}
        </CardHeader>
        <CardContent>
          <Empty>
            <ChartNoAxesCombined aria-hidden="true" />
            <EmptyHeader>
              <EmptyTitle>Capture cannot be computed</EmptyTitle>
              <EmptyDescription>
                Capture requires generation and a regional price for the same interval. Unpriced generation is skipped
                rather than valued at a substituted price.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        </CardContent>
      </Card>
    );
  }

  const comparable = capture.timeWeightedPriceAudPerMwh > 0;

  return (
    <Card id="value-capture" className="capture-card">
      <CardHeader className="capture-header">
        <div>
          <p className="section-kicker">Value capture</p>
          <CardTitle>
            <h2 className="section-title">What each fuel earned in {capture.regionId}</h2>
          </CardTitle>
          <CardDescription>
            Capture rate is the volume-weighted price a fuel received divided by the region&apos;s time-weighted price
            of {formatPrice(capture.timeWeightedPriceAudPerMwh)} across {capture.intervalCount} interval
            {capture.intervalCount === 1 ? '' : 's'}. Above 1.00× means the fuel beat a passive position in the market.
          </CardDescription>
        </div>
        {regionSelect}
      </CardHeader>
      <CardContent>
        {!comparable && (
          <p className="capture-empty-note">
            The regional time-weighted price is {formatPrice(capture.timeWeightedPriceAudPerMwh)}, so no capture rate is
            shown. Dividing by a price at or below zero would invert the sign and display loss as outperformance.
            Revenue and negative-interval cost are still reported.
          </p>
        )}
        <ul className="capture-list">
          {capture.fuels.map((fuel) => (
            <CaptureRow key={fuel.token} fuel={fuel} />
          ))}
        </ul>
        <p className="capture-scale">
          Bars are clamped at {AXIS_MAX.toFixed(2)}× and the marker is the 1.00× regional baseline. Revenue is
          indicative energy value only: five-minute SCADA output at the regional reference price, excluding FCAS, loss
          factors, contracts, and settlement adjustment.
        </p>
      </CardContent>
    </Card>
  );
}
