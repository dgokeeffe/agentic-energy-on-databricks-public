import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@databricks/appkit-ui/react';
import { ArrowRightLeft, Banknote, Gauge, Moon, NotebookPen, Sun, TrendingDown, Zap } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { isSourceStale, type QueryState, type RegionStatus } from '../domain/regionStatus';
import {
  capturedRegions,
  formatAud,
  formatCaptureRate,
  formatMwh,
  formatPrice,
  mostExposedRegion,
  regionCapture,
  weakestCapture,
  type RegionPriceRow,
} from '../domain/fuelCapture';
import { formatMarketTime } from '../domain/time';
import { applyTheme, preferredTheme, type Theme } from '../lib/theme';
import { AppPurpose } from './AppPurpose';
import { JourneyHeader } from './JourneyHeader';
import { NemGeneratorMap } from './NemGeneratorMap';
import { GenerationByFuelChart } from './GenerationByFuelChart';
import { TopProducersChart } from './TopProducersChart';
import { FuelValueCapture } from './FuelValueCapture';
import { InvestigationPanel } from './InvestigationPanel';
import { QueryStateMessage } from './QueryState';
import { RevenueRestatement } from './RevenueRestatement';
import { SourceFreshness } from './SourceFreshness';

type ReadyState = Extract<QueryState, { kind: 'ready' }>;

function KpiCard({
  label,
  value,
  unit,
  period,
  source,
  detail,
  icon,
  negative = false,
}: {
  label: string;
  value: string;
  unit: string;
  period: string;
  source: string;
  detail: string;
  icon: React.ReactNode;
  negative?: boolean;
}) {
  return (
    <Card className={`kpi-card${negative ? ' kpi-negative' : ''}`}>
      <CardHeader className="kpi-header">
        <div>
          <CardDescription>{label}</CardDescription>
          <CardTitle className="kpi-value">{value}</CardTitle>
        </div>
        <span className="kpi-icon" aria-hidden="true">
          {icon}
        </span>
      </CardHeader>
      <CardContent className="kpi-meta">
        <p>
          <strong>{unit}</strong> · {period}
        </p>
        <p>{source}</p>
        <p>{detail}</p>
      </CardContent>
    </Card>
  );
}

/**
 * Light/dark switch.
 *
 * Separate from the theme module so the module stays free of React and can be
 * called once before first paint without mounting a component.
 */
function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => preferredTheme());

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const next: Theme = theme === 'dark' ? 'light' : 'dark';
  return (
    <button
      type="button"
      className="theme-toggle"
      aria-label={next === 'dark' ? 'Switch to dark theme' : 'Switch to light theme'}
      onClick={() => setTheme(next)}
    >
      {theme === 'dark' ? <Sun size={15} aria-hidden="true" /> : <Moon size={15} aria-hidden="true" />}
    </button>
  );
}

/** Governed price observations reduced to the fields value capture needs. */
function priceRows(rows: RegionStatus[]): RegionPriceRow[] {
  return rows.map((row) => ({
    intervalEnd: row.intervalEnd,
    regionId: row.regionId,
    rrpAudPerMwh: row.rrpAudPerMwh,
    priceSourceRunNo: row.priceSourceRunNo,
  }));
}

function ReadyRegionalOperations({ state }: { state: ReadyState }) {
  const prices = useMemo(() => priceRows(state.rows), [state.rows]);
  const regions = useMemo(() => capturedRegions(prices), [prices]);
  // Open on the region with the weakest capture rather than the first
  // alphabetically, so the screen starts on the exposure worth explaining.
  const defaultRegion = useMemo(() => mostExposedRegion(state.fuelRows, prices), [state.fuelRows, prices]);
  const [requestedRegion, setRequestedRegion] = useState('');
  const [journalOpen, setJournalOpen] = useState(false);
  const lastJournalTrigger = useRef<HTMLButtonElement | null>(null);

  const first = state.rows[0];
  // Every hook below must run before any early return, so the region is resolved
  // defensively rather than after a guard.
  const selectedRegion = regions.includes(requestedRegion) ? requestedRegion : (defaultRegion ?? first?.regionId ?? '');
  const selectedRows = useMemo(
    () =>
      state.rows
        .filter((row) => row.regionId === selectedRegion)
        .sort((left, right) => Date.parse(left.intervalEnd) - Date.parse(right.intervalEnd)),
    [state.rows, selectedRegion]
  );

  const capture = useMemo(
    () => (state.fuelRows ? regionCapture(selectedRegion, state.fuelRows, prices) : null),
    [state.fuelRows, selectedRegion, prices]
  );

  // Revenue exposed to an AEMO re-run: only intervals whose price was restated.
  const restatedRevenueAud = useMemo(() => {
    if (!state.fuelRows || !capture) return 0;
    const restatedIntervals = new Set(
      prices
        .filter((price) => price.regionId === selectedRegion && price.priceSourceRunNo > 1)
        .map((price) => price.intervalEnd)
    );
    if (restatedIntervals.size === 0) return 0;
    const priceByInterval = new Map(
      prices
        .filter((price) => price.regionId === selectedRegion)
        .map((price) => [price.intervalEnd, price.rrpAudPerMwh])
    );
    return state.fuelRows
      .filter((row) => row.regionId === selectedRegion && restatedIntervals.has(row.intervalEnd))
      .reduce(
        (total, row) => total + row.actualGenerationMw * (5 / 60) * (priceByInterval.get(row.intervalEnd) ?? 0),
        0
      );
  }, [state.fuelRows, capture, prices, selectedRegion]);

  if (!first) return <QueryStateMessage kind="empty" />;
  const focusedRow = selectedRows.at(-1);
  if (!focusedRow) {
    return <QueryStateMessage kind="error" message="The selected region has no represented observations." />;
  }

  const weakest = capture ? weakestCapture(capture) : null;
  const focusedRowStale = isSourceStale(focusedRow, state.evaluatedAtMs);
  const period = formatMarketTime(focusedRow.intervalEnd);
  const windowStart = selectedRows[0] ? formatMarketTime(selectedRows[0].intervalEnd) : period;
  const modeLabel = state.mode === 'mock' ? 'Prepared non-live fixture' : 'Prepared snapshot integration';
  const negativeCost = capture?.totalNegativePriceCostAud ?? 0;

  return (
    <Sheet open={journalOpen} onOpenChange={setJournalOpen}>
      <div className="app-nav-shell">
        <div className="app-nav">
          <a className="app-brand" href="#overview" aria-label="NEM value capture overview">
            <span className="brand-mark" aria-hidden="true">
              <Zap size={17} />
            </span>
            <span>NEM value capture</span>
          </a>
          <nav aria-label="Primary navigation">
            <a href="#value-capture">Value capture</a>
            <a href="#restatement">Restatement</a>
            <a href="#purpose">Purpose</a>
            <a href="#market-context">Market context</a>
            <SheetTrigger asChild>
              <Button
                size="sm"
                onClick={(event) => {
                  lastJournalTrigger.current = event.currentTarget;
                }}
              >
                <NotebookPen aria-hidden="true" />
                Investigate
              </Button>
            </SheetTrigger>
            <ThemeToggle />
          </nav>
        </div>
      </div>

      <main className="app-shell">
        <JourneyHeader activeStep={2} provenanceLabel={modeLabel} stale={state.stale} />

        <header id="overview" className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Wholesale value capture · {selectedRegion}</p>
            {capture && weakest ? (
              <>
                <h1>
                  {weakest.label} captured{' '}
                  <span className="hero-headline-figure">{formatCaptureRate(weakest.captureRate)}</span> of the{' '}
                  {selectedRegion} average price
                </h1>
                <p className="hero-summary">
                  {formatMwh(weakest.energyMwh)} sold at {formatPrice(weakest.volumeWeightedPriceAudPerMwh)} against a
                  regional time-weighted {formatPrice(capture.timeWeightedPriceAudPerMwh)}.{' '}
                  {capture.negativePriceIntervalCount > 0
                    ? `${capture.negativePriceIntervalCount} of ${capture.intervalCount} intervals priced below zero.`
                    : 'No interval in this window priced below zero.'}{' '}
                  Prepared snapshot values, never live market evidence.
                </p>
              </>
            ) : (
              <>
                <h1>Value capture is unavailable for {selectedRegion}</h1>
                <p className="hero-summary">
                  {state.fuelRows === null
                    ? 'The governed generation read returned nothing, so no revenue or capture figure is computed. Regional price and freshness below are unaffected.'
                    : 'No generation matched a priced interval for this region. Unpriced generation is skipped rather than valued at a substituted price.'}
                </p>
              </>
            )}
          </div>
          <div className="hero-period" aria-label="Reporting window">
            <span>Reporting window</span>
            <strong>{windowStart}</strong>
            <strong>{period}</strong>
            <small>Fixed AEST (UTC+10, no daylight saving)</small>
          </div>
        </header>

        <section className="kpi-grid" aria-label="Value capture summary">
          <KpiCard
            label="Indicative energy revenue"
            value={capture ? formatAud(capture.totalRevenueAud) : 'Unavailable'}
            unit="AUD, all fuels"
            period={selectedRegion}
            source="SCADA output × regional reference price"
            detail="Excludes FCAS, loss factors, contracts, and settlement adjustment"
            icon={<Banknote size={22} />}
            negative={capture ? capture.totalRevenueAud < 0 : false}
          />
          <KpiCard
            label="Negative-price exposure"
            value={
              !capture
                ? 'Unavailable'
                : capture.negativePriceIntervalCount === 0
                  ? 'No exposure'
                  : formatAud(negativeCost)
            }
            unit={
              !capture || capture.negativePriceIntervalCount === 0
                ? 'No interval priced below zero'
                : negativeCost < 0
                  ? 'AUD lost'
                  : 'AUD earned'
            }
            period={`${capture?.negativePriceIntervalCount ?? 0} of ${capture?.intervalCount ?? 0} intervals below zero`}
            source="Intervals with a negative dispatch price"
            detail="Generating into a negative price destroys value; consuming into one earns"
            icon={<TrendingDown size={22} />}
            negative={negativeCost < 0}
          />
          <KpiCard
            label="Regional time-weighted price"
            value={capture ? formatPrice(capture.timeWeightedPriceAudPerMwh) : 'Unavailable'}
            unit="AUD/MWh"
            period={`${capture?.intervalCount ?? selectedRows.length} intervals`}
            source="NEMWEB DISPATCHIS, effective run only"
            detail="The capture-rate baseline: what a flat position would have received"
            icon={<Gauge size={22} />}
          />
          <KpiCard
            label="Energy represented"
            value={capture ? formatMwh(capture.totalEnergyMwh) : 'Unavailable'}
            unit="Signed net, all fuels"
            period={selectedRegion}
            source="NEMWEB DISPATCH_UNIT_SCADA"
            detail="Actual output, never a dispatch target or availability"
            icon={<ArrowRightLeft size={22} />}
          />
        </section>

        {/* One notice row rather than up to three stacked full-width banners.
            Staleness against a prepared fixture is an expected property of the
            fixture, so it is stated without the alarm styling that a live
            deployment warrants; the instruction not to treat the values as
            current is identical in both modes. */}
        {(state.stale || state.fuelRows === null || state.unitRows === null || state.predictionStale) && (
          <ul className="notice-row" aria-label="Data quality notices">
            {state.stale && (
              <li
                className={state.mode === 'mock' ? 'notice notice-muted' : 'notice notice-alert'}
                role={state.mode === 'mock' ? 'status' : 'alert'}
              >
                <strong>Stale source</strong>
                {state.mode === 'mock' ? ', as expected for a prepared fixture' : ''}: the newest
                represented market interval is more than 15 minutes old. Do not treat these values as
                current.
              </li>
            )}
            {/* The diagnostic, not just the symptom: a deployer needs to know it
                is a grant, not an outage. */}
            {state.fuelRows === null && (
              <li className="notice notice-muted" role="status">
                <strong>Generation read unavailable</strong> — in a deployed workspace this normally
                means the app&apos;s service principal lacks SELECT on the governed generation tables.
              </li>
            )}
            {state.unitRows === null && (
              <li className="notice notice-muted" role="status">
                <strong>Per-unit read unavailable</strong> — the map and unit ranking need SELECT on{' '}
                <code>gold_nem_unit_dispatch_5min</code>, granted separately from price and demand.
              </li>
            )}
            {state.predictionStale && (
              <li className="notice notice-muted" role="status">
                <strong>Prediction inputs stale</strong> — governed market price and demand freshness
                is reported separately.
              </li>
            )}
          </ul>
        )}

        <div className="panel-pair">
          <GenerationByFuelChart rows={state.fuelRows} regionId={selectedRegion} />
          <TopProducersChart rows={state.unitRows} />
        </div>

        <NemGeneratorMap rows={state.unitRows} />

        <FuelValueCapture
          capture={capture}
          regions={regions}
          selectedRegion={selectedRegion}
          onRegionChange={setRequestedRegion}
        />

        {capture && (
          <RevenueRestatement
            capture={capture}
            goldPublishedAt={focusedRow.goldPublishedAt}
            restatedRevenueAud={restatedRevenueAud}
          />
        )}

        <AppPurpose />

        <Card id="regional-observations" className="data-table-card">
          <CardHeader>
            <CardTitle>
              <h2 className="section-title">Underlying five-minute prices</h2>
            </CardTitle>
            <CardDescription>
              The governed observations behind every figure above. Negative dispatch prices remain valid; market time is
              fixed AEST.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="table-scroll">
              <Table aria-label="Regional dispatch price and demand">
                <TableCaption>Governed effective-run observations, newest interval first.</TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Region</TableHead>
                    <TableHead>Interval end</TableHead>
                    <TableHead className="numeric">Dispatch price</TableHead>
                    <TableHead className="numeric">Demand</TableHead>
                    <TableHead>Source run</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {state.rows.map((row) => (
                    <TableRow key={`${row.regionId}|${row.intervalEnd}`} data-focused={row.regionId === selectedRegion}>
                      <TableCell className="region-cell">{row.regionId}</TableCell>
                      <TableCell>{formatMarketTime(row.intervalEnd)}</TableCell>
                      <TableCell className="numeric">{formatPrice(row.rrpAudPerMwh)}</TableCell>
                      <TableCell className="numeric">{row.totalDemandMw.toFixed(1)} MW</TableCell>
                      <TableCell>
                        P{row.priceSourceRunNo} · D{row.demandSourceRunNo}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <section id="market-context" className="lower-grid" aria-labelledby="market-context-heading">
          <Card>
            <CardHeader>
              <CardTitle>
                <h2 id="market-context-heading" className="section-title">
                  Market-wide context
                </h2>
              </CardTitle>
              <CardDescription>
                Repeated on each regional row; shown once and never summed across regions.
              </CardDescription>
            </CardHeader>
            <CardContent className="context-grid">
              <div>
                <span>Binding constraints</span>
                <strong>{first.marketWideBindingConstraintCount}</strong>
                <small>market-wide count</small>
              </div>
              <div>
                <span>Interconnectors</span>
                <strong>{first.marketWideInterconnectorCount}</strong>
                <small>market-wide count</small>
              </div>
              <div>
                <span>Interconnector flow</span>
                <strong>
                  {first.marketWideInterconnectorSourceSignFlowMw < 0 ? '−' : ''}
                  {Math.abs(first.marketWideInterconnectorSourceSignFlowMw).toFixed(1)} MW
                </strong>
                <small>AEMO source sign</small>
              </div>
              <p className="context-note">
                No regional allocation or directional interpretation is inferred because no governed
                interconnector-to-region mapping is available.
              </p>
            </CardContent>
          </Card>

          <SourceFreshness row={focusedRow} stale={focusedRowStale} />
        </section>

        <Card id="investigate" className="decision-cta">
          <CardContent>
            <div>
              <p className="section-kicker">Analyst workflow</p>
              <h2>Investigate the observation with Genie</h2>
              <p>
                Ask for a prepared analysis of {focusedRow.regionId} at {formatMarketTime(focusedRow.intervalEnd)}, then
                review and save the follow-up note. Identity comes from the trusted application context.
              </p>
            </div>
            <SheetTrigger asChild>
              <Button
                size="lg"
                onClick={(event) => {
                  lastJournalTrigger.current = event.currentTarget;
                }}
              >
                <NotebookPen aria-hidden="true" />
                Investigate with Genie
              </Button>
            </SheetTrigger>
          </CardContent>
        </Card>

        <footer className="app-disclaimer">
          <p>
            Visual design adapted from{' '}
            <a href="https://github.com/opennem/openelectricity" rel="noreferrer">
              Open Electricity
            </a>
            , MIT licensed, © 2023-2026 Open Electricity. Its fuel-technology colours are reused here as a display
            vocabulary. This is a Databricks workshop demonstration and is not affiliated with, endorsed by, or produced
            for Open Electricity, AEMO, or any market participant.
          </p>
          <p>
            Revenue and capture figures are indicative energy value only: five-minute SCADA output at the regional
            reference price, excluding FCAS, loss factors, contracts, and settlement adjustment. Curtailment is not
            derivable, because AEMO Current publishes no five-minute availability. Values are prepared snapshot data
            with fixed-AEST market intervals and UTC processing timestamps, and are never live market evidence.
          </p>
        </footer>
      </main>

      <SheetContent
        id="investigation-journal"
        side="right"
        className="journal-sheet"
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          lastJournalTrigger.current?.focus();
        }}
      >
        <SheetHeader className="sr-only">
          <SheetTitle>Investigation assistant</SheetTitle>
          <SheetDescription>Review a prepared analysis and save an investigation for the selected region and interval.</SheetDescription>
        </SheetHeader>
        <InvestigationPanel row={focusedRow} />
      </SheetContent>
    </Sheet>
  );
}

export function RegionalOperationsShell({ state }: { state: QueryState }) {
  if (state.kind === 'loading') return <QueryStateMessage kind="loading" />;
  if (state.kind === 'empty') return <QueryStateMessage kind="empty" />;
  if (state.kind === 'error') return <QueryStateMessage kind="error" message={state.message} />;
  return <ReadyRegionalOperations state={state} />;
}
