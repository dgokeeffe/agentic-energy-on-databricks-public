#!/usr/bin/env bash
set -euo pipefail

if ! command -v bd >/dev/null 2>&1; then
  echo "bd is required; install Beads before bootstrapping participant work." >&2
  exit 1
fi

if [ -d .beads/embeddeddolt ]; then
  echo "Participant Beads is already initialized."
  bd ready
  exit 0
fi

bd init --init-if-missing --non-interactive --skip-agents --skip-hooks \
  --prefix agentic-energy

create_issue() {
  local title="$1"
  local issue_type="$2"
  local priority="$3"
  local labels="$4"
  local description="$5"
  printf '%s\n' "$description" | bd create "$title" --stdin \
    --type="$issue_type" --priority="$priority" --labels="$labels" --silent
}

foundation_id="$(create_issue \
  'Foundation: run the deterministic fixture ETL' task 1 participant,foundation \
  'Run the checked-in fixture profile and verify Bronze, Silver, Quarantine, Gold, and manifest reconciliation. Record commands and evidence; do not enable live sources.')"

metadata_id="$(create_issue \
  'Engineering: inspect and improve the metadata contract' task 1 participant,engineering \
  'Inspect source metadata, schema, timezone, natural key, watermark, quality, and quarantine behavior. Make a bounded contract or test improvement without creating a source-specific job.')"

quarantine_id="$(create_issue \
  'Defect: malformed rows are not safely quarantined' bug 1 participant,lane-b \
  'Investigate the seeded malformed-row symptom. Trace the contract and cite file/line evidence. Propose a safe patch and tests; do not disclose or assume the intended fix from the issue title.')"

timezone_id="$(create_issue \
  'Defect: local market timestamps are not normalized correctly' bug 1 participant,lane-b \
  'Investigate the seeded timezone symptom across daylight-saving boundaries. Produce evidence, a bounded patch proposal, and regression tests without changing source terms or deployment permissions.')"

sync_id="$(create_issue \
  'Defect: synchronized Gold reconciliation is inconsistent' bug 1 participant,lane-b \
  'Investigate the seeded synchronized-Gold key/count/freshness symptom. Verify the documented read-only boundary and propose evidence-backed tests and remediation.')"

identity_id="$(create_issue \
  'Defect: annotation access does not enforce identity boundaries' bug 1 participant,lane-b \
  'Investigate the seeded annotation authorization symptom. Trace caller identity, writable native state, audit fields, and read-only governed data. Propose tests and a safe patch.')"

for issue_id in "$metadata_id" "$quarantine_id" "$timezone_id" "$sync_id" "$identity_id"; do
  bd dep add "$issue_id" "$foundation_id"
done

touch .beads/.participant-seeded

echo "Participant Beads initialized. Ready work:"
bd ready
