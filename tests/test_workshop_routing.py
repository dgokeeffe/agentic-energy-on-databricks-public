from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = (
    "AGENTS.md", "CLAUDE.md", "README.md", "QUICKSTART.md", "PRE-REQUISITES.md",
    "docs/agent-pr-workflow.md", "docs/challenge-spec.md",
    "docs/participant/workshop-playbook.md", "docs/participant/workshop-pair-record.md",
    "docs/facilitator/workshop-run-of-show.md", "docs/facilitator/workshop-fallback.md",
    "docs/facilitator/workshop-acceptance.md", "docs/facilitator/workshop-status-board.md",
    "presentations/coda-workshop-agenda.md", "presentations/coda-workshop-deck.md",
)


def test_active_navigation_uses_shared_github_issue_lifecycle_not_retained_lanes():
    text = "\n".join((ROOT / path).read_text() for path in ACTIVE)
    for forbidden in ("lane_a_business/", "lane_b_engineering/"):
        assert forbidden not in text
    for required in (
        "workshop-ready", "measurable requirement", "human approval",
        "deterministic test", "agentic eval", "independent", "pull request",
        "accept", "send back", "reject", "stop",
    ):
        assert required.lower() in text.lower(), required


def test_all_shared_lifecycle_skills_exist_and_link_forward():
    names = (
        "issue-navigator", "understand-requirement", "plan-change", "implement-test",
        "agentic-eval", "adversarial-review", "prepare-pull-request",
    )
    for name in names:
        path = ROOT / ".agents/skills" / name / "SKILL.md"
        assert path.is_file(), name
        assert "GitHub" in path.read_text() or name != "issue-navigator"
