/**
 * Guided journey header, after the GridSense Intelligence Hub landing.
 *
 * The step list is deliberately this repository's journey. It supports
 * exploration with prepared evidence today, and leaves room for a released
 * Genie Agent without pretending that one is already connected.
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
  { n: 4, label: 'Investigate', detail: 'Review the evidence with Genie' },
  { n: 5, label: 'Learn', detail: 'Change feed returns it to analytics' },
] as const;

export interface JourneyHeaderProps {
  /** Which step the reader is on, for the current highlight. */
  activeStep?: number;
  /**
   * Provenance label for the whole page, e.g. "Prepared non-live fixture" or
   * "Prepared snapshot integration".
   *
   * There is deliberately no `live` flag. Both data modes this app supports read
   * prepared data, so a boolean invited exactly the bug it produced: the header
   * rendered a pulsing green live dot beside the word "Prepared". If a genuinely
   * live mode is added, give it its own explicit state rather than inferring
   * liveness from the absence of mock mode.
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
            NEMWEB landing &rarr; Bronze &rarr; correction-aware Silver &rarr; five-minute Gold &rarr; this app.
            Writable state is Lakebase; analytics reads stay lakehouse-owned.
          </p>
        </div>
        {/* The single provenance badge for the page. Sections deliberately do not
            repeat it. No live indicator: nothing this app reads is live. */}
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
