"""Local teaching-fixture contracts, not a test of agent behaviour or live data."""

from copy import deepcopy
import json
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRACTICE = ROOT / "workshop/agent-practice"
LINKS = runpy.run_path(str(ROOT / "scripts/validate-miniwiki.py"))
SOURCE_REFS = [
    "README.md#governed-nemweb-analytics-on-databricks",
    "nemweb_foundation/DATA-CONTRACT.md#fixed-data-semantics",
    "nemweb_foundation/DATA-CONTRACT.md#report-to-subject-contract",
]
SKILLS = ("understand-requirement", "plan-change", "agentic-eval", "adversarial-review")
RECORD_FIELDS = (
    "Task kind, preparation choice, and verification rationale",
    "Explanations ruled out with cited evidence, versus paths not investigated",
    "Refinement, defect correction, restart, or block, with a short reason when relevant",
    "Structural-review result, location, consequence, and remaining uncertainty",
    'Proposed lesson or "do not generalise"; original and second-case inputs/results; keep/revise/discard decision',
)


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def fixture(name):
    return json.loads((PRACTICE / name).read_text(encoding="utf-8"))


def prose(relative):
    return " ".join(read(relative).lower().split())


class AgentPracticeTests(unittest.TestCase):
    def assert_source_refs(self, refs):
        self.assertEqual(refs, SOURCE_REFS)
        for ref in refs:
            path, fragment = LINKS["resolve_link"](ROOT / "README.md", ref)
            self.assertTrue(path.is_file(), ref)
            self.assertIn(fragment, LINKS["heading_slugs"](path), ref)

    def assert_case_contract(self, case):
        """Validate these two teaching cases, not a production observation schema."""
        self.assertEqual(set(case), {
            "case_id", "evidence_kind", "live_evidence", "origin", "question",
            "observations", "source_refs", "limitations",
        })
        self.assertIn(case["case_id"], ("zero-generation", "missing-generation"))
        self.assertEqual(case["evidence_kind"], "synthetic/non-live")
        self.assertIs(case["live_evidence"], False)
        self.assertIn("no real unit identifiers, customer data, or live observations", case["origin"])
        self.assertIn("actual_generation_mw", case["question"])
        self.assertIn("unit availability", case["question"])
        self.assert_source_refs(case["source_refs"])
        self.assertEqual(len(case["limitations"]), 3)
        limits = " ".join(case["limitations"])
        self.assertIn("No authoritative T+1 unit-solution record", limits)
        self.assertIn("No live workspace or source was queried", limits)
        observations = case["observations"]
        if case["case_id"] == "zero-generation":
            self.assertEqual(observations, [{"sample": "reported-zero", "actual_generation_mw": 0}])
            # bool is a subclass of int: False must not masquerade as the zero case.
            self.assertIs(type(observations[0]["actual_generation_mw"]), int)
            self.assertIn("not a runtime ingestion fixture", limits)
        else:
            self.assertEqual(observations, [
                {"sample": "null-field", "actual_generation_mw": None},
                {"sample": "omitted-field"},
            ])
            self.assertIn("not an asserted runtime schema", limits)

    def test_fixture_facts_and_non_live_provenance(self):
        for name in ("zero-generation", "missing-generation"):
            with self.subTest(case=name):
                case = fixture(f"cases/{name}.json")
                self.assertEqual(case["case_id"], name)
                self.assert_case_contract(case)

    def test_missing_is_not_zero_and_both_missing_forms_are_present(self):
        zero = fixture("cases/zero-generation.json")["observations"][0]
        missing = fixture("cases/missing-generation.json")["observations"]
        self.assertEqual(zero["actual_generation_mw"], 0)
        self.assertIn("actual_generation_mw", missing[0])
        self.assertIsNone(missing[0]["actual_generation_mw"])
        self.assertNotIn("actual_generation_mw", missing[1])
        for observation in missing:
            self.assertNotEqual(observation.get("actual_generation_mw"), 0)

    def test_rejects_zero_case_type_and_value_drift(self):
        for value in (None, False, True, "0", [], {}):
            with self.subTest(value=value):
                case = fixture("cases/zero-generation.json")
                case["observations"][0]["actual_generation_mw"] = value
                with self.assertRaises(AssertionError):
                    self.assert_case_contract(case)

    def test_rejects_missing_coercion_or_loss_of_representation(self):
        original = fixture("cases/missing-generation.json")
        for index in (0, 1):
            case = deepcopy(original)
            case["observations"][index]["actual_generation_mw"] = 0
            with self.subTest(index=index), self.assertRaises(AssertionError):
                self.assert_case_contract(case)
        case = deepcopy(original)
        case["observations"].pop()
        with self.assertRaises(AssertionError):
            self.assert_case_contract(case)

    def test_rejects_malformed_or_live_teaching_metadata(self):
        mutations = (
            ("live_evidence", True), ("live_evidence", "false"),
            ("live_evidence", 0), ("evidence_kind", "live"),
            ("source_refs", []), ("case_id", "unknown"),
            ("observations", []), ("origin", "collected observation"),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                case = fixture("cases/zero-generation.json")
                case[key] = value
                with self.assertRaises(AssertionError):
                    self.assert_case_contract(case)
        case = fixture("cases/zero-generation.json")
        case["observations"][0]["unit_id"] = "unexpected-identifier"
        with self.assertRaises(AssertionError):
            self.assert_case_contract(case)

    def test_answer_key_expectations_are_separate_and_source_based(self):
        key = fixture("expected-findings.json")
        self.assertEqual(key["evidence_kind"], "facilitator-prepared/non-live")
        self.assertIs(key["live_evidence"], False)
        self.assertIn("not an investigator input or an actual agent result", key["audience"])
        self.assert_source_refs(key["source_refs"])
        self.assertEqual(set(key["cases"]), {"zero-generation", "missing-generation"})
        self.assertEqual(key["cases"]["zero-generation"]["output_conclusion"], "reported-zero")
        self.assertEqual(key["cases"]["missing-generation"]["output_conclusion"], "not-established")
        for case in key["cases"].values():
            self.assertEqual(case["availability_conclusion"], "not-established")
            self.assertTrue(case["required_findings"])
            self.assertTrue(case["ruled_out"])
            self.assertTrue(case["not_investigated"])
            self.assertIn("authoris", case["evidence_needed"])
        basis = " ".join(key["source_basis"])
        self.assertIn("Current reports do not publish five-minute unit availability", basis)
        self.assertIn("Next_Day_Dispatch UNIT_SOLUTION", basis)
        self.assertIn("Missing is not zero", basis)
        self.assertIn("do not coerce either to zero", " ".join(key["cases"]["missing-generation"]["required_findings"]))
        self.assertIn("neither physical state is ruled out", " ".join(key["cases"]["missing-generation"]["ruled_out"]))
        self.assertIn("does not rule out an unavailable unit", " ".join(key["cases"]["zero-generation"]["ruled_out"]))
        self.assertIn("do not prove model behaviour", " ".join(key["review_limits"]))

    def test_source_contract_still_supports_prepared_distinction(self):
        # Presence/consistency checks require independent semantic review as well.
        intro = prose("README.md")
        manifest = prose("nemweb_foundation/DATA-CONTRACT.md")
        self.assertIn("actual_generation_mw", intro)
        self.assertIn("next_day_dispatch at t+1", intro)
        self.assertIn("current reports do not publish five-minute unit availability", manifest)
        self.assertIn("authoritative target and availability belong only in the daily t+1 unit-solution product", manifest)

    def test_track_record_has_exactly_the_five_learning_fields(self):
        text = read("workshop/track-record-template.md")
        rows = [line.split("|")[1].strip() for line in text.splitlines() if line.startswith("| ")]
        for field in RECORD_FIELDS:
            self.assertEqual(rows.count(field), 1, field)
        for label in ("actual agent output", "actual human output", "facilitator-prepared output", "not-run"):
            self.assertIn(label, text)
        self.assertIn("prompt versions, baseline and", text)
        self.assertIn("replay outputs", text)

    def test_task_preparation_and_proof_are_integrated_without_new_permissions(self):
        requirement = prose(".agents/skills/understand-requirement/SKILL.md")
        plan = prose(".agents/skills/plan-change/SKILL.md")
        for kind in ("repetitive task", "small repair", "new component or multi-step change", "investigation", "translation or migration"):
            self.assertIn(kind, requirement)
        self.assertIn("task type never grants permissions", requirement)
        self.assertIn("a person who did not draft the plan must approve it before implementation", plan)
        self.assertIn("no task kind grants permissions or waives a required gate", plan)
        self.assertIn("shared-skill or test change outside the original approved plan", plan)
        for name in SKILLS:
            text = read(f".agents/skills/{name}/SKILL.md")
            self.assertIn("track-record-template.md", text)
            self.assertIn("maintenance", text)

    def test_eval_distinguishes_reasoning_and_legitimate_no_change_outcomes(self):
        text = prose(".agents/skills/agentic-eval/SKILL.md")
        for concept in ("explanations ruled out", "paths not investigated", "useful refinement", "defect correction", "restart", "block"):
            self.assertIn(concept, text)
        self.assertIn("useful refinement is not automatically a failure", text)
        self.assertIn("no extra instruction needed", text)
        self.assertIn("do not generalise", text)
        self.assertIn("any required criterion scored as failed returns the change", text)
        self.assertIn("no participant must create a new skill", text)

    def test_review_separates_behaviour_and_structure_and_preserves_floor(self):
        text = prose(".agents/skills/adversarial-review/SKILL.md")
        for concept in ("behavioural review", "structural review", "responsibilities", "dependencies", "duplication", "interfaces", "location and consequence", "remaining uncertainty", "no material issue found", "not applicable"):
            self.assertIn(concept, text)
        self.assertIn("reviewer other than the author", text)
        self.assertIn("unavailable reviewers leave the gate incomplete", text)
        self.assertIn("a prompt alone does not enforce read-only access", text)
        self.assertIn("only a final `pass` proceeds", text)
        self.assertIn("small change: 2 reviewers", prose(".agents/skills/agentic-verification/SKILL.md"))

    def test_exercise_has_packet_separation_prompts_replay_and_fallback(self):
        text = prose("workshop/agent-practice/README.md")
        for heading in ("## investigator prompt", "## reviewer prompt", "## answer-key separation", "## run and retain the comparison"):
            self.assertIn(heading, text)
        self.assertIn("give the investigator only its prompt, one case, and the cited source passages", text)
        self.assertIn("not this full readme, the test file, previous outputs, reviewer notes", text)
        self.assertIn("do not ask the investigator to copy an answer key", text)
        self.assertIn("replay both the original and variant in fresh sessions", text)
        self.assertIn("same baseline prompt", text)
        self.assertIn("constrained fresh session", text)
        self.assertIn("if restrictions cannot be verified, use a human", text)
        self.assertIn("fallbacks do not reduce that floor", text)
        self.assertIn("no extra instruction needed", text)
        self.assertIn("do not generalise", text)
        self.assertIn("keep/revise/discard", text)
        self.assertIn("not a blinded benchmark", text)
        self.assertIn("do not prove agent behaviour", text)

    def test_record_and_exercise_preserve_placement_and_review_gates(self):
        # The withdrawn playbook's gate vocabulary now lives in the track record and
        # the exercise README. The "only clock source" requirement is deliberately
        # absent: see miniwiki/decisions/track-structure.md.
        for path in ("workshop/track-record-template.md", "workshop/agent-practice/README.md"):
            with self.subTest(path=path):
                text = prose(path)
                for concept in ("approved plan", "facilitator", "required check", "read-only replay", "later approved task", "not-run"):
                    self.assertIn(concept, text)
                self.assertIn("facilitator-prepared output", text)
                self.assertIn("actual agent output", text)
        record = prose("workshop/track-record-template.md")
        self.assertIn("do not mutate the repository after final review", record)
        self.assertIn("accepts, sends back, rejects, or stops", record)

    def test_changed_markdown_links_resolve(self):
        paths = [f".agents/skills/{name}/SKILL.md" for name in SKILLS] + [
            "workshop/track-record-template.md",
            "workshop/agent-practice/README.md",
        ]
        for relative in paths:
            page = ROOT / relative
            for target in LINKS["LINK_RE"].findall(page.read_text(encoding="utf-8")):
                with self.subTest(page=relative, target=target):
                    resolved = LINKS["resolve_link"](page, target)
                    if resolved is None:
                        continue
                    path, fragment = resolved
                    self.assertTrue(path.exists(), target)
                    if fragment and path.suffix == ".md":
                        self.assertIn(fragment.lower(), LINKS["heading_slugs"](path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
