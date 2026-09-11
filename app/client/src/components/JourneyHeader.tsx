/**
 * Guided journey header, after the GridSense Intelligence Hub landing.
 *
 * The step list is deliberately this repository's journey. It supports
 * exploration with prepared evidence today, and leaves room for recorded
 * investigation with provenance.
 */

interface JourneyStep {
  n: number;
  label: string;
  detail: string;
}

const STEPS: readonly JourneyStep[] = [
  { n: 1, label: 'Observe', detail: 'Governed five-minute price and demand' },
  { n: 2, label: 'Locate', detail: 'Where the fleet is actually generating' },
  { n: 3, label: 'Explain', detail: 'Which fuels captured the price' },
  { n: 4, label: 'Investigate', detail: 'Review the evidence and record a note' },
  { n: 5, label: 'Record', detail: 'Save the follow-up in Lakebase' },
] as const;

export interface JourneyHeaderProps {
  /** Which step the reader is on, for the current highlight. */
  activeStep?: number;
  /**
   * Provenance label for the whole page, e.g. "Prepared non-live fixture" or
   * "Snapshot data via Lakebase".
   *
   * Source provenance is separate from freshness; a live source can be stale.
   */
  provenanceLabel: string;
  /** Newest represented interval is older than the staleness threshold. */
  stale: boolean;
}

export function JourneyHeader({ activeStep, provenanceLabel, stale }: JourneyHeaderProps) {
  // The landmark is labelled explicitly rather than by its own heading. Pointing
  // aria-labelledby at the visible title gave this region the accessible name
  // "From governed NEMWEB data to a recorded decision", which collided with the
  // investigation journal's "Decision" field: getByLabel('Decision') matched both
  // the region and the textarea, and a screen-reader user got two "Decision"
  // targets. The heading stays visible and in the heading order; only the
  // landmark's accessible name is narrowed.
  return (
    <section className="journey-card" aria-label="Guided journey">
      <div className="journey-intro">
        <p className="section-kicker">Closed-loop regional operations</p>
        <h2 id="journey-title" className="journey-title">
          From governed NEMWEB data to a useful investigation
        </h2>
        {/* One orienting line only. The Problem/Outcome pair that used to sit here
            restated the purpose card below ('The question it answers', 'Why it
            matters now'), which is the section that owns the argument. This header
            owns the sequence and the provenance. */}
        <p className="journey-body">
          Each figure below carries its provenance, so an observation can be followed to the fleet that produced it and
          the decision it justified.
        </p>
      </div>

      <div className="journey-side">
        <div className="journey-provenance">
          <p className="journey-provenance-title">Data path</p>
          <p>
            NEMWEB landing &rarr; Bronze &rarr; correction-aware Silver &rarr; five-minute Gold &rarr; Delta serving &rarr; Lakebase &rarr; this app.
            Lakebase serves market data and stores investigation notes.
          </p>
        </div>
        {/* The single provenance badge for the page. Sections deliberately do not
            repeat it. Freshness is reported separately from source mode. */}
        <div className="journey-badges">
          <span className="journey-badge journey-badge-prepared">{provenanceLabel}</span>
          {stale && <span className="journey-badge journey-badge-stale">Source stale</span>}
        </div>
      </div>

      <ol className="journey-steps">
        {STEPS.map((step) => {
          const state =
            activeStep === undefined
              ? 'idle'
              : step.n === activeStep
                ? 'current'
                : step.n < activeStep
                  ? 'done'
                  : 'idle';
          return (
            <li key={step.n} className={`journey-step journey-step-${state}`}>
              <span className="journey-step-n" aria-hidden="true">
                {step.n}
              </span>
              <span className="journey-step-text">
                <strong>{step.label}</strong>
                <small>{step.detail}</small>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
