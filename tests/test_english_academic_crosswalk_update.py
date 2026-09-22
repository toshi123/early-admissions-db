from __future__ import annotations

import csv
import hashlib
import unittest
from collections import Counter
from pathlib import Path

from early_admissions.academic_field_v2 import AcademicFieldV2Contract
from early_admissions.english_academic_crosswalk_update import build_and_audit
from early_admissions.english_requirement import EnglishRequirementCrosswalk

from tests.test_validator import REPO_ROOT


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EnglishAcademicCrosswalkUpdateTests(unittest.TestCase):
    def test_review_decision_counts_and_semantics(self) -> None:
        decisions = rows(
            REPO_ROOT
            / "validation/reports/update_20260922_v5_81_v1_08/english_requirement_human_review_decisions_v0_2.csv"
        )
        self.assertEqual(len(decisions), 66)
        self.assertEqual(
            Counter(row["final_status"] for row in decisions),
            {"required": 57, "not_required": 3, "review_required": 5, "unknown": 1},
        )
        self.assertEqual(decisions[19]["final_status"], "review_required")
        self.assertEqual(decisions[44]["final_status"], "unknown")
        self.assertEqual(decisions[63]["final_status"], "required")

    def test_active_english_crosswalk_is_exact_and_complete(self) -> None:
        path = REPO_ROOT / "schema/english_requirement/english_requirement_crosswalk_v0_2.csv"
        crosswalk = EnglishRequirementCrosswalk.load(path, expected_version="0.2")
        self.assertEqual(len(crosswalk), 243)
        decisions = rows(
            REPO_ROOT
            / "validation/reports/update_20260922_v5_81_v1_08/english_requirement_human_review_decisions_v0_2.csv"
        )
        for decision in decisions:
            self.assertEqual(
                crosswalk.classify(decision["raw_value"]).requirement_status,
                decision["final_status"],
            )
        self.assertEqual(crosswalk.classify("未監査の新規表現").requirement_status, "unmapped")

    def test_reviewed_contexts_are_authoritative_exact_overrides(self) -> None:
        contract = AcademicFieldV2Contract.load(REPO_ROOT)
        cases = (
            (
                ("kokkoritsu", "九州大学", "経済学部", "経済工学科", "経済・工学"),
                ("economics",),
            ),
            (
                ("kokkoritsu", "神戸大学", "国際人間科学部", "発達コミュニティ学科", "人間科学"),
                ("humanities_social_general",),
            ),
        )
        for key, expected in cases:
            result = contract.classify(
                source_dataset=key[0], university=key[1], faculty_school=key[2],
                department=key[3], academic_field=key[4],
            )
            self.assertEqual(result.context_mapping_effect, "authoritative")
            self.assertEqual(tuple(row[0] for row in result.broad_memberships), expected)

    def test_builder_is_byte_deterministic_and_focused_audit_passes(self) -> None:
        first = build_and_audit(REPO_ROOT)
        targets = (
            REPO_ROOT / "schema/english_requirement/english_requirement_crosswalk_v0_2.csv",
            REPO_ROOT / "schema/academic_field/academic_field_crosswalk_v0_2.csv",
            REPO_ROOT / "schema/academic_field/v0_3/academic_field_raw_crosswalk_v0_3.csv",
            REPO_ROOT / "schema/academic_field/v0_3/academic_field_context_crosswalk_v0_3.csv",
        )
        first_hashes = [sha(path) for path in targets]
        second = build_and_audit(REPO_ROOT)
        self.assertEqual(first_hashes, [sha(path) for path in targets])
        self.assertEqual(first["status"], "passed")
        self.assertEqual(second["prohibited_unmapped"], {
            "english": 0, "academic_v0_1": 0, "academic_v0_2": 0,
        })


if __name__ == "__main__":
    unittest.main()
