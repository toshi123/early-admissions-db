from __future__ import annotations

import csv
import unittest
from collections import Counter
from pathlib import Path

from early_admissions.academic_field import (
    ACADEMIC_FIELD_CROSSWALK_PATH, AcademicFieldCrosswalk, AcademicFieldTaxonomy,
)
from early_admissions.academic_field_v2 import AcademicFieldV2Contract
from early_admissions.english_requirement import (
    ENGLISH_REQUIREMENT_CROSSWALK_PATH,
    EnglishRequirementCrosswalk,
)
from early_admissions.grade_requirement import GradeRequirementCrosswalk

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "validation/reports/crosswalk_20270928_v0_3/raw_decisions.csv"


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class CurrentCrosswalkReviewTests(unittest.TestCase):
    def test_english_v0_5_preserves_v0_4_and_audits_batch_values(self) -> None:
        old = read(ROOT / "schema/english_requirement/english_requirement_crosswalk_v0_4.csv")
        current_path = ROOT / ENGLISH_REQUIREMENT_CROSSWALK_PATH
        current = read(current_path)
        self.assertEqual(current_path.name, "english_requirement_crosswalk_v0_5.csv")
        normalized = [{**row, "contract_version": current[0]["contract_version"]} for row in old]
        for row in normalized:
            self.assertIn(row, current)
        crosswalk = EnglishRequirementCrosswalk.load(current_path)
        additions = {
            "個別の英語資格要件なし。": "not_required",
            "英語資格要件の詳細は募集要項の資格経路別条件を参照。Unknown。": "review_required",
            "TOEFL iBT 32点以上（旧スコア換算、2024年12月～2026年12月受験、My Best Scores不可）。": "required",
            "TOEFL又はIELTS Academic-moduleのスコア提出（2024-04-01以降受験）。": "required",
            "TOEIC L&R（公開テスト）のスコア提出。100点換算（スコア÷6.5、650点以上は100点）。": "required",
            "TOEFL又はIELTSの外部英語試験成績を提出（英語母語者を除く）。": "required",
        }
        for raw, expected in additions.items():
            self.assertEqual(crosswalk.classify(raw).requirement_status, expected)
        self.assertEqual(crosswalk.classify('TOEFL iBT、TOEIC(L＆R)又はIELTS(Academic Module)のいずれかを受験し、成績証明書を提出（最低スコア基準の明示なし）。').requirement_status, "required")

    def test_prior_exact_decisions_are_preserved(self) -> None:
        for old_path, new_path, version_col in (
            ("schema/english_requirement/english_requirement_crosswalk_v0_2.csv", "schema/english_requirement/english_requirement_crosswalk_v0_3.csv", "contract_version"),
            ("schema/grade_requirement/grade_requirement_crosswalk_v0_2.csv", "schema/grade_requirement/grade_requirement_crosswalk_v0_3.csv", "contract_version"),
            ("schema/academic_field/academic_field_crosswalk_v0_2.csv", "schema/academic_field/academic_field_crosswalk_v0_3.csv", "mapping_contract_version"),
            ("schema/academic_field/v0_3/academic_field_raw_crosswalk_v0_3.csv", "schema/academic_field/v0_4/academic_field_raw_crosswalk_v0_4.csv", "mapping_contract_version"),
            ("schema/academic_field/v0_3/academic_field_context_crosswalk_v0_3.csv", "schema/academic_field/v0_4/academic_field_context_crosswalk_v0_4.csv", "mapping_contract_version"),
        ):
            old = read(ROOT / old_path)
            new = read(ROOT / new_path)
            normalized = [{**row, version_col: new[0][version_col]} for row in old]
            for row in normalized:
                self.assertIn(row, new)

    def test_review_decisions_are_exact_and_provenanced(self) -> None:
        decisions = read(DECISIONS)
        self.assertEqual(Counter(row["layer"] for row in decisions), {
            "english": 10, "grade": 6, "academic_v1": 2, "academic_v2": 2,
        })
        self.assertEqual(Counter((row["layer"], row["decision"]) for row in decisions), {
            ("english", "required"): 6,
            ("english", "not_required"): 1,
            ("english", "review_required"): 3,
            ("grade", "unknown"): 2,
            ("grade", "review_required"): 4,
            ("academic_v1", "review_required"): 2,
            ("academic_v2", "review_required"): 2,
        })
        english = EnglishRequirementCrosswalk.load(ROOT / "schema/english_requirement/english_requirement_crosswalk_v0_4.csv")
        grade = GradeRequirementCrosswalk.load(ROOT / "schema/grade_requirement/grade_requirement_crosswalk_v0_3.csv")
        taxonomy = AcademicFieldTaxonomy.load(ROOT / "schema/academic_field/academic_field_taxonomy_v0_1.csv")
        academic = AcademicFieldCrosswalk.load(ROOT / ACADEMIC_FIELD_CROSSWALK_PATH, taxonomy)
        AcademicFieldV2Contract.load(ROOT)
        for row in decisions:
            self.assertTrue(row["example_record_ids"])
            self.assertTrue(row["official_source_urls"].startswith("https://"))
            raw, expected = row["raw_value"], row["decision"]
            if row["layer"] == "english":
                result = english.classify(raw)
                self.assertEqual(result.requirement_status, expected)
                self.assertEqual(result.parse_status, "exact_crosswalk")
            elif row["layer"] == "grade":
                result = grade.classify(raw)
                self.assertEqual(result.grade_requirement_status, expected)
                self.assertIsNone(result.overall_gpa_min_tenths)
            elif row["layer"] == "academic_v1":
                result = academic.lookup(raw)
                self.assertEqual(result.mapping_status, expected)
                self.assertEqual(result.group_codes, ())


if __name__ == "__main__":
    unittest.main()
