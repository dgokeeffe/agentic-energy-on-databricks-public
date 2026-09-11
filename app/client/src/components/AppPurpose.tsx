import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@databricks/appkit-ui/react';
import { Banknote, ShieldAlert, TrendingDown, Users } from 'lucide-react';

const PURPOSE_ITEMS = [
  {
    icon: <Users size={18} />,
    label: 'Who it is for',
    body: 'A portfolio analyst or asset performance team reviewing how a generation fleet performed against the market it sold into.',
    boundary: false,
  },
  {
    icon: <Banknote size={18} />,
    label: 'The question it answers',
    body: 'Which fuels captured the regional price, which gave value away, and what the negative-price intervals cost.',
    boundary: false,
  },
  {
    icon: <TrendingDown size={18} />,
    label: 'Why it matters now',
    body: 'Midday used to be premium. With renewables above half of NEM supply in recent quarters, low and negative prices have moved the economics of every fuel in the stack.',
    boundary: false,
  },
  {
    icon: <ShieldAlert size={18} />,
    label: 'What it cannot tell you',
    body: 'Curtailment. AEMO Current publishes no five-minute availability, so withheld output cannot be quantified here — only output that ran and the price it earned. Not for bids, live operation, or settlement.',
    boundary: true,
  },
];

export function AppPurpose() {
  return (
    <Card id="purpose" className="purpose-card">
      <CardHeader>
        <p className="section-kicker">Purpose</p>
        <CardTitle>
          <h2 className="section-title">Find where the value went, then record what you decided</h2>
        </CardTitle>
        <CardDescription>
          Governed NEMWEB dispatch and SCADA data, resolved to one commercial measure per fuel, with the provenance that
          explains why the figure can change.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="purpose-grid">
          {PURPOSE_ITEMS.map((item) => (
            <li key={item.label} className={item.boundary ? 'purpose-boundary' : undefined}>
              <span className="purpose-icon" aria-hidden="true">
                {item.icon}
              </span>
              <div>
                <h3>{item.label}</h3>
                <p>{item.body}</p>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
