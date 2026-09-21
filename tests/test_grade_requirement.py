from __future__ import annotations

import csv
import unittest
from collections import Counter

from early_admissions.grade_requirement import (
    GRADE_REQUIREMENT_CROSSWALK_PATH,
    GradeRequirementCrosswalk,
)

from tests.test_validator import REPO_ROOT


RIKKYO_RAW = (
    "全体の評定平均値3.8以上。加えて、出願条件5(a)ルートでは学科指定科目の"
    "評定平均値4.5以上。5(b)～(e)の活動・海外教育経験ルートでも出願可。"
)


class GradeRequirementCrosswalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = REPO_ROOT / GRADE_REQUIREMENT_CROSSWALK_PATH
        cls.crosswalk = GradeRequirementCrosswalk.load(cls.path)

    def test_freeze_covers_all_current_non_null_raw_values_exactly(self) -> None:
        with (REPO_ROOT / "validation/reports/gpa_requirement_raw_value_audit_v0_1.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            audit = list(csv.DictReader(handle))
        non_null = [row for row in audit if row["primary_class"] != "null"]
        self.assertEqual(len(non_null), 553)
        self.assertEqual(len(self.crosswalk), 553)
        self.assertFalse(
            [
                row["raw_value"]
                for row in non_null
                if self.crosswalk.classify(row["raw_value"]).grade_requirement_status
                == "unmapped"
            ]
        )

    def test_frozen_distinct_and_admission_weighted_counts(self) -> None:
        with (REPO_ROOT / "validation/reports/gpa_requirement_raw_value_audit_v0_1.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            source_rows = list(csv.DictReader(handle))
        weights = {row["raw_value"]: int(row["row_count"]) for row in source_rows}
        with self.path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        status_distinct = Counter(row["grade_requirement_status"] for row in rows)
        overall_distinct = Counter(row["overall_gpa_status"] for row in rows)
        status_rows = Counter()
        overall_rows = Counter()
        for row in rows:
            status_rows[row["grade_requirement_status"]] += weights[row["raw_value"]]
            overall_rows[row["overall_gpa_status"]] += weights[row["raw_value"]]
        status_distinct["unknown"] += 1
        overall_distinct["unknown"] += 1
        status_rows["unknown"] += weights[""]
        overall_rows["unknown"] += weights[""]

        self.assertEqual(
            dict(status_distinct),
            {
                "unknown": 36,
                "required": 403,
                "review_required": 72,
                "not_required": 32,
                "not_applicable": 11,
            },
        )
        self.assertEqual(
            dict(status_rows),
            {
                "unknown": 1985,
                "required": 2286,
                "review_required": 1291,
                "not_required": 339,
                "not_applicable": 20,
            },
        )
        self.assertEqual(sum(status_rows.values()), 5921)
        self.assertEqual(
            dict(overall_distinct),
            {
                "unknown": 35,
                "safe_simple_overall": 96,
                "ambiguous": 71,
                "no_safe_overall_floor": 266,
                "safe_overall_with_additional_conditions": 65,
                "not_applicable": 11,
                "non_admission_numeric": 3,
                "non_binding": 5,
                "historical": 2,
            },
        )
        self.assertEqual(
            dict(overall_rows),
            {
                "unknown": 1984,
                "safe_simple_overall": 1206,
                "ambiguous": 1284,
                "no_safe_overall_floor": 1269,
                "safe_overall_with_additional_conditions": 123,
                "not_applicable": 20,
                "non_admission_numeric": 7,
                "non_binding": 26,
                "historical": 2,
            },
        )
        self.assertEqual(sum(overall_rows.values()), 5921)

    def test_rikkyo_is_required_with_a_safe_overall_floor_and_additional_conditions(self) -> None:
        result = self.crosswalk.classify(RIKKYO_RAW)
        self.assertEqual(result.grade_requirement_status, "required")
        self.assertEqual(result.overall_gpa_min_tenths, 38)
        self.assertEqual(result.overall_gpa_min_inclusive, 1)
        self.assertEqual(
            result.overall_gpa_status,
            "safe_overall_with_additional_conditions",
        )
        self.assertEqual(result.additional_grade_conditions, 1)

    def test_subject_only_and_qualitative_are_required_without_an_overall_floor(self) -> None:
        for raw in (
            "数学・理科とも3.8以上",
            "学習成績概評A段階",
            "数値基準なし（『成績優秀にして大学専門教育に適する者』）。",
        ):
            with self.subTest(raw=raw):
                result = self.crosswalk.classify(raw)
                self.assertEqual(result.grade_requirement_status, "required")
                self.assertIsNone(result.overall_gpa_min_tenths)

    def test_simple_compound_and_branch_numeric_contract(self) -> None:
        simple = self.crosswalk.classify("全体の学習成績の状況3.8以上。")
        self.assertEqual(simple.overall_gpa_min_tenths, 38)
        self.assertEqual(simple.overall_gpa_status, "safe_simple_overall")
        self.assertEqual(simple.additional_grade_conditions, 0)

        compound = self.crosswalk.classify(
            "全体の学習成績の状況3.8以上、かつ数学・理科それぞれ4.0以上"
        )
        self.assertEqual(compound.overall_gpa_min_tenths, 38)
        self.assertEqual(
            compound.overall_gpa_status,
            "safe_overall_with_additional_conditions",
        )
        self.assertEqual(compound.additional_grade_conditions, 1)

        branch = self.crosswalk.classify(
            "全体の学習成績の状況3.5以上、または大学指定英語資格・検定スコア条件を満たすこと。"
        )
        self.assertEqual(branch.grade_requirement_status, "required")
        self.assertIsNone(branch.overall_gpa_min_tenths)

    def test_requirement_vs_selection_use_review_is_fail_closed(self) -> None:
        cases = {
            "明示的な数値基準なし（高等学校の成績が優秀であることを選抜基準とする）。": "not_required",
            "評定平均等の基準なし（IB指定履修科目は成績評価5以上）。": "required",
            "数値による評定要件なし。": "review_required",
            "IB資格取得（見込み）等の出願資格による。日本の評定平均基準は公開大綱では確認できない。": "unknown",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                result = self.crosswalk.classify(raw)
                self.assertEqual(result.grade_requirement_status, expected)
                self.assertIsNone(result.overall_gpa_min_tenths)

    def test_non_requirement_historical_nonbinding_and_non_admission_values_have_no_floor(self) -> None:
        cases = {
            "評定基準なし。調査書等は選考資料として30点で評価。": "not_required",
            "全体の学習成績の状況4.3以上が望ましい": "not_required",
            "2026年度参考：全体の学習成績の状況4.3以上": "unknown",
            "全体の学習成績の状況4.0以上で入学料全額免除、3.2以上で半額免除。": "not_required",
        }
        for raw, status in cases.items():
            with self.subTest(raw=raw):
                result = self.crosswalk.classify(raw)
                self.assertEqual(result.grade_requirement_status, status)
                self.assertIsNone(result.overall_gpa_min_tenths)

    def test_null_and_future_values_fail_closed(self) -> None:
        missing = self.crosswalk.classify(None)
        self.assertEqual(missing.grade_requirement_status, "unknown")
        self.assertEqual(missing.parse_status, "missing")
        future = self.crosswalk.classify("将来追加された未監査表現4.0以上")
        self.assertEqual(future.grade_requirement_status, "unmapped")
        self.assertEqual(future.overall_gpa_status, "unmapped")
        self.assertIsNone(future.overall_gpa_min_tenths)


if __name__ == "__main__":
    unittest.main()
