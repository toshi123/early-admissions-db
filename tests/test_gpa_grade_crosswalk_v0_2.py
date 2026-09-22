from __future__ import annotations

import csv
import json
import unittest
from collections import Counter

from early_admissions.gpa_grade_crosswalk_v0_2 import (
    CANDIDATE_AUDIT_JSON_PATH,
    DECISION_PATH,
    GPA_CROSSWALK_PATH,
    GRADE_CROSSWALK_PATH,
    MANIFEST_PATH,
    PREVIOUS_GPA_CROSSWALK_PATH,
    PREVIOUS_GRADE_CROSSWALK_PATH,
    build_artifact_bytes,
    candidate_audit_summary,
    load_decisions,
    sha256_path,
    verify_packet_correspondence,
)
from early_admissions.gpa_search import GPACrosswalk, GPAParser
from early_admissions.grade_requirement import GradeRequirementCrosswalk

from tests.test_validator import REPO_ROOT


DECISION_SHA256 = "a9610e5acc0b3c6071c2a24a8a12bfe05b886601e8a5d1a3c0b63eb8e23fe438"
PREVIOUS_GPA_SHA256 = "d111046ce752c2c5ecc4585e1551811e125b23290d4daeb14e496f4fcee24563"
PREVIOUS_GRADE_SHA256 = "9b09a7d8c91fb8837fb974c441e9975ed26a02fcb656684a7db304804859882c"
REVIEW_REQUIRED_ORDERS = [8, 10, 11, 12, 13, 14, 15, 45, 49, 52, 53, 54, 56]
RIKKYO_CANDIDATE_RAW = (
    "全体の評定平均値3.8以上。出願条件5(a)では学科指定科目の評定平均値4.5以上"
    "（高卒同等資格の一部は評定条件なし）。"
)


class GPAGradeCrosswalkV02FreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decisions = load_decisions(REPO_ROOT)

    def test_human_decision_artifact_and_packet_correspondence_are_frozen(self) -> None:
        self.assertEqual(sha256_path(REPO_ROOT / DECISION_PATH), DECISION_SHA256)
        self.assertEqual(
            verify_packet_correspondence(REPO_ROOT, self.decisions),
            {"status": "passed", "rows": 63, "mismatches": 0},
        )
        self.assertEqual(
            [
                int(row["review_order"])
                for row in self.decisions
                if row["approved_grade_status"] == "review_required"
            ],
            REVIEW_REQUIRED_ORDERS,
        )

    def test_reviewed_decision_counts_are_exact(self) -> None:
        self.assertEqual(
            Counter(row["approved_grade_status"] for row in self.decisions),
            Counter(required=35, not_required=10, unknown=5, review_required=13),
        )
        self.assertEqual(
            Counter(row["approved_numeric_status"] for row in self.decisions),
            Counter(
                safe_simple_overall=11,
                safe_overall_with_additional_conditions=18,
                no_safe_overall_floor=6,
                non_binding=9,
                non_admission_numeric=1,
                historical=1,
                ambiguous=13,
                unknown=4,
            ),
        )
        self.assertEqual(
            Counter(row["approved_overall_floor"] or "NULL" for row in self.decisions),
            Counter({"NULL": 34, "4.0": 16, "3.8": 8, "3.5": 2, "4.1": 2, "4.3": 1}),
        )

    def test_versioned_outputs_rebuild_byte_identically(self) -> None:
        generated = build_artifact_bytes(REPO_ROOT)
        self.assertEqual(set(generated), {GPA_CROSSWALK_PATH, GRADE_CROSSWALK_PATH, MANIFEST_PATH})
        for relative, data in generated.items():
            with self.subTest(path=relative):
                self.assertEqual(data, (REPO_ROOT / relative).read_bytes())

        manifest = json.loads((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
        self.assertEqual(manifest["previous_version"], "0.1")
        self.assertEqual(manifest["version"], "0.2")
        self.assertEqual(manifest["reviewed_on"], "2026-09-22")
        self.assertEqual(manifest["review_source"], "human review")
        self.assertEqual(
            manifest["candidate_sources"], {"kokkoritsu": "5.81", "shidai": "1.08"}
        )
        self.assertEqual(
            manifest["inputs"]["previous_gpa_crosswalk"]["sha256"],
            PREVIOUS_GPA_SHA256,
        )
        self.assertEqual(
            manifest["inputs"]["previous_grade_crosswalk"]["sha256"],
            PREVIOUS_GRADE_SHA256,
        )

    def test_all_reviewed_values_are_known_and_unsafe_rules_have_no_strict_floor(self) -> None:
        gpa = GPACrosswalk.load(REPO_ROOT / GPA_CROSSWALK_PATH)
        grade = GradeRequirementCrosswalk.load(
            REPO_ROOT / GRADE_CROSSWALK_PATH, expected_version="0.2"
        )
        self.assertEqual(len(gpa), 617)
        self.assertEqual(len(grade), 616)
        for decision in self.decisions:
            raw = decision["raw_value"]
            with self.subTest(order=decision["review_order"]):
                self.assertIsNotNone(gpa.get(raw))
                result = grade.classify(raw)
                self.assertNotEqual(result.grade_requirement_status, "unmapped")
                expected_floor = (
                    int(decision["approved_overall_floor_tenths"])
                    if decision["approved_overall_floor_tenths"]
                    else None
                )
                self.assertEqual(result.overall_gpa_min_tenths, expected_floor)
                if expected_floor is None:
                    self.assertIsNone(result.additional_grade_conditions)
                    parsed = GPAParser(gpa).parse(
                        raw,
                        admission_year=2027,
                        information_year=2027,
                        fallback_previous_year=False,
                    )
                    self.assertIsNone(parsed.gpa_min_tenths)

    def test_candidate_focused_audit_before_after_and_rikkyo(self) -> None:
        summary = candidate_audit_summary(REPO_ROOT)
        frozen = json.loads(
            (REPO_ROOT / CANDIDATE_AUDIT_JSON_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(summary, frozen)
        self.assertEqual(summary["scope"]["candidate_admissions"], 6411)
        self.assertEqual(summary["scope"]["affected_admissions"], 596)
        self.assertEqual(
            summary["exact_crosswalk_unmapped"]["affected_admissions"],
            {
                "gpa_unmapped_after": 0,
                "gpa_unmapped_before": 596,
                "grade_unmapped_after": 0,
                "grade_unmapped_before": 596,
            },
        )
        self.assertEqual(summary["review_required"]["review_orders"], REVIEW_REQUIRED_ORDERS)
        self.assertEqual(summary["review_required"]["affected_admissions"], 128)
        rikkyo = summary["rikkyo_2027_sci_03"]
        self.assertEqual(rikkyo["review_order"], 41)
        self.assertEqual(rikkyo["grade_requirement_status"], "required")
        self.assertEqual(rikkyo["overall_gpa_min_tenths"], 38)
        self.assertEqual(
            rikkyo["overall_gpa_status"],
            "safe_overall_with_additional_conditions",
        )
        self.assertEqual(rikkyo["strict_gpa_parse_status"], "conditional_review")
        self.assertIsNone(rikkyo["strict_gpa_min_tenths"])
        self.assertEqual(rikkyo["english_requirement_status"], "required")
        self.assertEqual(rikkyo["english_search_disposition"], "safe_exact")

    def test_production_snapshot_results_are_logically_unchanged(self) -> None:
        previous_gpa = GPAParser(
            GPACrosswalk.load(REPO_ROOT / PREVIOUS_GPA_CROSSWALK_PATH)
        )
        current_gpa = GPAParser(GPACrosswalk.load(REPO_ROOT / GPA_CROSSWALK_PATH))
        previous_grade = GradeRequirementCrosswalk.load(
            REPO_ROOT / PREVIOUS_GRADE_CROSSWALK_PATH, expected_version="0.1"
        )
        current_grade = GradeRequirementCrosswalk.load(
            REPO_ROOT / GRADE_CROSSWALK_PATH, expected_version="0.2"
        )
        compared = 0
        historical_paths = (
            REPO_ROOT
            / "data/releases/kokkoritsu-v5.61/"
            "kokkoritsu_early_admissions_2027_master_v5_61.csv",
            REPO_ROOT
            / "data/releases/shidai-v0.97/"
            "shidai_early_admissions_2027_master_v0_97.csv",
        )
        for path in historical_paths:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    compared += 1
                    raw = row["gpa_requirement"] or None
                    kwargs = {
                        "admission_year": int(row["admission_year"]),
                        "information_year": int(row["information_year"]),
                        "fallback_previous_year": (
                            row["fallback_previous_year"].lower() == "true"
                        ),
                    }
                    self.assertEqual(
                        previous_gpa.parse(raw, **kwargs),
                        current_gpa.parse(raw, **kwargs),
                    )
                    before = previous_grade.classify(raw)
                    after = current_grade.classify(raw)
                    self.assertEqual(
                        (
                            before.raw_value,
                            before.grade_requirement_status,
                            before.overall_gpa_min_tenths,
                            before.overall_gpa_min_inclusive,
                            before.overall_gpa_status,
                            before.additional_grade_conditions,
                            before.parse_status,
                            before.review_note,
                        ),
                        (
                            after.raw_value,
                            after.grade_requirement_status,
                            after.overall_gpa_min_tenths,
                            after.overall_gpa_min_inclusive,
                            after.overall_gpa_status,
                            after.additional_grade_conditions,
                            after.parse_status,
                            after.review_note,
                        ),
                    )
        self.assertEqual(compared, 5921)
        self.assertEqual(
            current_grade.classify(RIKKYO_CANDIDATE_RAW).overall_gpa_min_tenths,
            38,
        )


if __name__ == "__main__":
    unittest.main()
