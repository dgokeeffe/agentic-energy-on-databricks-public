# Participant Beads

This repository uses Beads for the participant work graph. The generated Dolt
working database is intentionally local and ignored; only the public
configuration, formulas, and bootstrap instructions are tracked here.

Initialize the participant graph from a clean clone:

```bash
scripts/bootstrap-participant-beads.sh
bd ready
```

Each laptop owns an independent local Beads database. The bootstrap script uses
stable public issue IDs so the same issue can be referenced consistently in
branches and pull requests, but `bd update --claim` is only a local claim.
Participants must follow the facilitator's team assignment to avoid duplicate
work.

A Dolt remote may be used by an organizer for backup or later reconciliation,
but participants must not depend on network access to Beads. Do not copy private
organizer databases or solution notes into this repository.
