import { useMemo, useState } from 'react';
import { MapPin, Radio } from 'lucide-react';
import facilitiesJson from '../data/topology/nemFacilities.json';
import {
  joinFacilitiesToDispatch,
  latestIntervalRows,
  peakAbsoluteMw,
  radiusFor,
  regionAnchors,
  regionTotals,
  type MappedFacility,
  type NemFacility,
  type UnitDispatchRow,
} from '../domain/facilityMap';
import { formatMarketTime } from '../domain/time';

/**
 * Real NEM generator map.
 *
 * Positions come from a static public coordinate reference (435 facilities, 572
 * DUIDs; see data/topology/ATTRIBUTION.md). Every megawatt comes from the
 * governed `gold_nem_unit_dispatch_5min` read. Nothing on this surface is
 * synthetic, and nothing is a dispatch target: AEMO Current publishes no
 * five-minute unit availability, so the map cannot and does not show curtailment.
 *
 * There is no basemap. Drawing a coastline would need either a vector borders
 * file or a tile provider; the first adds a dependency and a licence for
 * decoration, and the second makes a third-party network request from a
 * governed workshop app. ~435 stations trace the eastern seaboard and the
 * inland valleys well enough to be legible, and the region bands carry the rest.
 */

const VIEW = { width: 800, height: 520 } as const;

const FACILITIES = facilitiesJson as NemFacility[];

/**
 * Region label and shading positions, computed once from the full coordinate
 * reference. Static input, so this is module-level rather than a hook.
 *
 * These position text and background shading only. They are never used to
 * attribute a value to a region: region membership always comes from the
 * governed `region_id` on the dispatch row.
 */
const ANCHORS = regionAnchors(facilitiesJson as NemFacility[], VIEW);

function formatMw(value: number): string {
  const rounded = Math.round(value);
  const sign = rounded < 0 ? '−' : '';
  return `${sign}${Math.abs(rounded).toLocaleString('en-AU')} MW`;
}

function fuelColour(token: MappedFacility['token']): string {
  return `var(--fuel-${token})`;
}

export interface NemGeneratorMapProps {
  /**
   * Governed per-unit rows, or null when that read is unavailable.
   *
   * Null is a first-class state: the map needs a third Unity Catalog grant, so an
   * unprivileged deployment must lose this section explicitly rather than render
   * an empty map that looks like a grid with nothing running.
   */
  rows: UnitDispatchRow[] | null;
}

export function NemGeneratorMap({ rows }: NemGeneratorMapProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const latest = useMemo(() => (rows ? latestIntervalRows(rows) : []), [rows]);
  const { facilities, coverage } = useMemo(() => joinFacilitiesToDispatch(FACILITIES, latest, VIEW), [latest]);
  const peak = useMemo(() => peakAbsoluteMw(facilities), [facilities]);
  const totals = useMemo(() => regionTotals(facilities), [facilities]);

  const focused = facilities.find((facility) => facility.facilityCode === selected) ?? null;
  const intervalEnd = latest[0]?.intervalEnd;

  const netMw = facilities.reduce((total, facility) => total + facility.netGenerationMw, 0);
  const chargingCount = facilities.filter((facility) => facility.netGenerationMw < 0).length;

  if (rows === null) {
    return (
      <section className="map-card" aria-labelledby="map-title">
        <div className="map-head">
          <div>
            <p className="section-kicker">Locate</p>
            <h2 id="map-title" className="panel-title">
              Where the fleet is generating
            </h2>
          </div>
        </div>
        <p className="panel-empty">
          The per-unit generation read is unavailable. This surface needs <code>SELECT</code> on{' '}
          <code>gold_nem_unit_dispatch_5min</code> in the app serving schema, which is granted separately from regional
          price and demand.
        </p>
      </section>
    );
  }

  return (
    <section className="map-card" aria-labelledby="map-title">
      <div className="map-head">
        <div>
          <p className="section-kicker">Locate</p>
          <h2 id="map-title" className="panel-title">
            Where the fleet is generating
          </h2>
          <p className="panel-note">
            {formatMw(netMw)} net{intervalEnd ? <> at {formatMarketTime(intervalEnd)}</> : null}. Area is proportional
            to output; colour is the station&rsquo;s dominant fuel.
          </p>
        </div>
        {/* No mode badge here. The journey header already carries one for the
            whole page, and repeating it per section put "Prepared non-live
            fixture" on screen three times. */}
        <p className="panel-figure numeric">
          {coverage.facilitiesDrawn.toLocaleString('en-AU')}
          <small>stations reporting</small>
        </p>
      </div>

      <div className="map-layout">
        <div className="map-canvas-wrap">
          <svg
            className="map-canvas"
            viewBox={`0 0 ${VIEW.width} ${VIEW.height}`}
            role="img"
            aria-label={`Map of ${coverage.facilitiesDrawn} reporting NEM generators, sized by output and coloured by fuel`}
          >
            <defs>
              <radialGradient id="region-glow">
                <stop offset="0%" stopColor="var(--map-region-fill)" stopOpacity="0.95" />
                <stop offset="100%" stopColor="var(--map-region-fill)" stopOpacity="0" />
              </radialGradient>
            </defs>

            {/* Region shading, drawn first so stations sit above it. */}
            {ANCHORS.map((anchor) => (
              <circle
                key={`glow-${anchor.regionId}`}
                cx={anchor.x}
                cy={anchor.y}
                r={anchor.radius}
                fill="url(#region-glow)"
              />
            ))}

            {ANCHORS.map((anchor) => {
              const total = totals.find((entry) => entry.regionId === anchor.regionId);
              return (
                <g key={`label-${anchor.regionId}`} aria-hidden="true">
                  <text x={anchor.x} y={anchor.labelY} className="map-region-name">
                    {anchor.regionId}
                  </text>
                  {total ? (
                    <text x={anchor.x} y={anchor.labelY + 15} className="map-region-total">
                      {formatMw(total.netGenerationMw)}
                    </text>
                  ) : null}
                </g>
              );
            })}

            {facilities.map((facility) => {
              const radius = radiusFor(facility.netGenerationMw, peak);
              const charging = facility.netGenerationMw < 0;
              const isFocused = facility.facilityCode === selected;
              return (
                <g key={facility.facilityCode}>
                  {/* Stroked in the canvas colour rather than the fuel colour, so
                      overlapping stations stay countable. Without this, the four
                      coal sites merged into one dark blob at light-theme scale. */}
                  <circle
                    cx={facility.x}
                    cy={facility.y}
                    r={radius}
                    fill={fuelColour(facility.token)}
                    fillOpacity={charging ? 0.3 : 0.68}
                    stroke={charging ? fuelColour(facility.token) : 'var(--map-canvas)'}
                    strokeWidth={charging ? 1.4 : 1}
                    strokeDasharray={charging ? '2.5 2' : undefined}
                    className={isFocused ? 'map-dot map-dot-focused' : 'map-dot'}
                  />
                  {/* Hit area, so small stations remain clickable and reachable. */}
                  <circle
                    cx={facility.x}
                    cy={facility.y}
                    r={Math.max(radius, 11)}
                    fill="transparent"
                    className="map-hit"
                    tabIndex={0}
                    role="button"
                    aria-label={`${facility.facilityName}, ${facility.regionId}, ${facility.label}, ${formatMw(facility.netGenerationMw)}`}
                    aria-pressed={isFocused}
                    onClick={() => setSelected(isFocused ? null : facility.facilityCode)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        setSelected(isFocused ? null : facility.facilityCode);
                      }
                    }}
                  />
                </g>
              );
            })}
          </svg>
        </div>

        <aside className="map-aside">
          {focused ? (
            <div className="map-detail">
              <p className="map-detail-kicker">
                <MapPin size={13} aria-hidden="true" /> {focused.regionId}
              </p>
              <h3 className="map-detail-name">{focused.facilityName}</h3>
              <p className="map-detail-output numeric">{formatMw(focused.netGenerationMw)}</p>
              <p className="map-detail-fuel">
                <span className="fuel-swatch" style={{ background: fuelColour(focused.token) }} aria-hidden="true" />
                {focused.label}
                {focused.netGenerationMw < 0 ? ' · consuming' : null}
              </p>
              <dl className="map-detail-grid">
                <div>
                  <dt>Units reporting</dt>
                  <dd className="numeric">{focused.duids.length}</dd>
                </div>
                <div>
                  <dt>DUIDs</dt>
                  <dd className="mono map-detail-duids">{focused.duids.join(', ')}</dd>
                </div>
                <div>
                  <dt>Position</dt>
                  <dd className="numeric">
                    {focused.latitude.toFixed(3)}, {focused.longitude.toFixed(3)}
                  </dd>
                </div>
              </dl>
              <p className="map-detail-boundary">
                Metered output for this interval, not a dispatch target. No availability is published at five-minute
                grain, so nothing here shows withheld output.
              </p>
              <button type="button" className="map-clear" onClick={() => setSelected(null)}>
                Clear selection
              </button>
            </div>
          ) : (
            <div className="map-detail map-detail-empty">
              <p className="map-detail-kicker">
                <Radio size={13} aria-hidden="true" /> Select a station
              </p>
              <p>Choose any station to see its units, position, and metered output for this interval.</p>
              <dl className="map-detail-grid">
                <div>
                  <dt>Stations reporting</dt>
                  <dd className="numeric">{coverage.facilitiesDrawn.toLocaleString('en-AU')}</dd>
                </div>
                <div>
                  <dt>Units matched</dt>
                  <dd className="numeric">{coverage.duidsMatched.toLocaleString('en-AU')}</dd>
                </div>
                <div>
                  <dt>Consuming now</dt>
                  <dd className="numeric">{chargingCount.toLocaleString('en-AU')}</dd>
                </div>
              </dl>
            </div>
          )}

          <div className="map-legend">
            <p className="map-legend-title">Dominant fuel</p>
            <ul>
              {[...new Set(facilities.map((facility) => facility.token))].sort().map((token) => {
                const label = facilities.find((facility) => facility.token === token)?.label ?? token;
                return (
                  <li key={token}>
                    <span className="fuel-swatch" style={{ background: fuelColour(token) }} aria-hidden="true" />
                    {label}
                  </li>
                );
              })}
            </ul>
            <p className="map-legend-note">
              A dashed, paler dot is consuming rather than generating, such as a charging battery.
            </p>
          </div>
        </aside>
      </div>

      {/* The Open Electricity licence and attribution live once, in the page
          footer. Repeating "MIT licensed" here also made the footer's
          attribution ambiguous to a screen reader and to a test locator. */}
      <p className="map-coverage">
        Drawn from a static public coordinate reference of {FACILITIES.length} facilities, joined to governed per-unit
        output. {coverage.facilitiesWithoutOutput.toLocaleString('en-AU')} known facilities had no unit in this interval
        and are omitted rather than drawn at zero.
        {coverage.duidsWithoutCoordinates.length > 0 ? (
          <>
            {' '}
            {coverage.duidsWithoutCoordinates.length.toLocaleString('en-AU')} reporting{' '}
            {coverage.duidsWithoutCoordinates.length === 1 ? 'unit' : 'units'} carrying{' '}
            {formatMw(coverage.unmappedAbsoluteMw)} absolute output{' '}
            {coverage.duidsWithoutCoordinates.length === 1 ? 'has' : 'have'} no coordinate and{' '}
            {coverage.duidsWithoutCoordinates.length === 1 ? 'is' : 'are'} not on the map.
          </>
        ) : null}
      </p>
    </section>
  );
}
