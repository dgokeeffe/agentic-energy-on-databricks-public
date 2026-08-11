# Participant Beads

This repository uses Beads for the participant work graph. The generated Dolt
working database is intentionally local and ignored; only the public
configuration, formulas, and bootstrap instructions are tracked here.

Initialize the participant graph from a clean clone:

```bash
scripts/bootstrap-participant-beads.sh
bd ready
```

The workshop organizer may configure a public Beads Dolt remote after seeding
the graph. Participants should use `bd dolt pull` and `bd dolt push` only with
the remote supplied by the organizer. Do not copy private organizer databases
or solution notes into this repository.
