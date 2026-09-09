# Contributing

You do not need write access to this repository. Contribute by forking it and
opening a pull request. Everything below works from a fresh clone.

Workshop participants: you do not have to contribute anything. A track is
complete when you finish its own `Instructions.md`. Read this file only when you
want your change to land back in this repository.

## One-time setup

Install the GitHub CLI, then authenticate:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

Fork and clone in one step:

```bash
gh repo fork dgokeeffe/agentic-energy-on-databricks-public --clone --remote
cd agentic-energy-on-databricks-public
```

That leaves you with two remotes: `origin` (your fork, where you push) and
`upstream` (this repository, which you pull from).

Already cloned without forking? Add the fork afterwards:

```bash
gh repo fork --remote --remote-name origin
```

## Make a change

Start from an up-to-date `main`:

```bash
git checkout main
git pull --ff-only upstream main
git checkout -b your-change-name
```

Validate before you commit:

```bash
make validate-local
git diff --check
```

Both must succeed. If `make validate-local` fails for a reason unrelated to your
change, say so in the pull request rather than working around it.

Then commit and push to your fork:

```bash
git add <the files you changed>
git commit -m "Describe the change, not the process"
git push -u origin your-change-name
```

## Open the pull request

```bash
gh pr create --repo dgokeeffe/agentic-energy-on-databricks-public --fill
```

In the description, state:

- what changed and why,
- which commands you ran and their results,
- anything you are still uncertain about.

Report failures honestly. A pull request that says "one test still fails, here is
the output" is more useful than one that claims a pass it did not get.

## What lands easily

- The smallest change that addresses one thing.
- Documentation fixes, including stale links and wrong commands.
- A failing test that demonstrates a defect, with or without the fix.
- Changes that keep the fixed contracts: NEM market timestamps are
  interval-ending fixed AEST (UTC+10, no daylight saving); processing timestamps
  are timezone-aware UTC.

## What will be sent back

- Credentials, tokens, tenant details, or participant data in any file, log, or
  screenshot. Never commit these. If you have already pushed one, say so
  immediately rather than quietly force-pushing over it.
- A required check weakened, skipped, or deleted to obtain a pass.
- A second data store. All tracks read from the one governed NEMWEB foundation.
- Deployments, granted access, unpaused schedules, or enabled live data. These
  need explicit human authorisation and do not belong in a pull request from a
  fork.
- Unrelated reformatting mixed into a substantive change.

## Keeping your fork current

```bash
git checkout main
git pull --ff-only upstream main
git push origin main
```

## Notes for maintainers

`main` is protected: no force-pushes, no deletion, and changes arrive by pull
request. Pull requests do not require a second approving review, so a single
maintainer is never deadlocked. Administrators can still push directly to `main`
when something genuinely cannot wait — prefer not to.
