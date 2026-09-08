from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Entry points an attendee or assistant actually reads first.
ACTIVE = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "QUICKSTART.md",
    "PRE-REQUISITES.md",
)

TRACKS = (
    "lane_a_business/Instructions.md",
    "lane_b_engineering/Instructions.md",
    "workshop/track_c_app/Instructions.md",
)


def test_quickstart_routes_to_every_self_contained_track():
    """QUICKSTART is the chooser. It must offer all three tracks and no other path."""
    text = (ROOT / "QUICKSTART.md").read_text()
    for track in (
        "lane_a_business/Instructions.md",
        "lane_b_engineering/Instructions.md",
        "workshop/track_c_app/Instructions.md",
    ):
        assert track in text, track


def test_every_track_exists_and_declares_itself_self_contained():
    for track in TRACKS:
        path = ROOT / track
        assert path.is_file(), track
        text = path.read_text().lower()
        assert "self-contained" in text, f"{track} must state that it is self-contained"
        assert "track-record-template.md" in text, f"{track} must route to a track record"


def test_no_fixed_clock_remains_in_participant_material():
    """The run-of-show was withdrawn. No track may quote a wall-clock time or card."""
    forbidden = ("14:27", "run of show", "only clock source", "status board")
    for track in TRACKS:
        text = (ROOT / track).read_text().lower()
        for token in forbidden:
            assert token not in text, f"{track} still references '{token}'"


def test_tracks_do_not_depend_on_each_other():
    """Track A must not require a Track B owner, and vice versa."""
    forbidden = ("track a owner", "track b owner", "cross-track pair")
    for track in TRACKS:
        text = (ROOT / track).read_text().lower()
        for token in forbidden:
            assert token not in text, f"{track} still references '{token}'"


def test_active_entry_points_preserve_the_governed_vocabulary():
    text = "\n".join((ROOT / path).read_text() for path in ACTIVE).lower()
    for required in ("snapshot", "live", "aest", "utc", "not-run"):
        assert required in text, required


def test_all_shared_lifecycle_skills_exist_and_link_forward():
    names = (
        "issue-navigator", "understand-requirement", "plan-change", "implement-test",
        "agentic-eval", "adversarial-review", "prepare-pull-request",
    )
    for name in names:
        path = ROOT / ".agents/skills" / name / "SKILL.md"
        assert path.is_file(), name
        assert "GitHub" in path.read_text() or name != "issue-navigator"
