from __future__ import annotations

import csv
import hashlib
import io
import tempfile
import unittest
from collections import Counter
from contextlib import closing, redirect_stdout
from pathlib import Path
import sqlite3

from early_admissions.gpa_search import (
    GPA_AUDIT_PATH,
    GPA_RESULT_MEANING,
    GPAContractError,
    GPACrosswalk,
    GPAParser,
    parse_gpa_tenths,
    search_gpa,
)
from early_admissions.search_gpa import main as search_main
from early_admissions.sqlite_builder import SQLiteBuildPipeline

from tests.test_sqlite_build import prepare_unified_fixture
from tests.test_validator import REPO_ROOT


class GPAParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = GPAParser(GPACrosswalk.load(REPO_ROOT / GPA_AUDIT_PATH))

    def parse(self, raw: str | None, *, fallback: bool = False):
        return self.parser.parse(
            raw,
            admission_year=2027,
            information_year=2026 if fallback else 2027,
            fallback_previous_year=fallback,
        )

    def test_approved_simple_current_overall_minimum_is_safe(self) -> None:
        result = self.parse("全体の学習成績の状況3.8以上。")
        self.assertEqual(result.numeric_safety_tier, "safe_numeric")
        self.assertEqual(result.parse_status, "parsed_safe")
        self.assertEqual(result.gpa_min_tenths, 38)
        self.assertEqual(result.gpa_min_inclusive, 1)
        self.assertIsNone(result.gpa_max_tenths)

    def test_negative_fixtures_never_receive_parent_numeric_bounds(self) -> None:
        fixtures = {
            "subject": "数学および理科の学習成績の状況がそれぞれ4.0以上",
            "and": "全体の評定平均値4.3以上かつ学修成績概評A。",
            "or": "3.0以上、または所定資格等",
            "branch": "学習成績の状況3.2以上。PASCAL入試チャレンジプログラム修了者は3.0以上。",
            "non_binding": "全体の学習成績の状況4.3以上が望ましい",
            "non_admission": "全体の学習成績の状況4.0以上で入学料全額免除、3.2以上で半額免除。",
            "unknown": "不明",
            "new_unapproved": "全体の学習成績の状況3.8以上（新規・未監査）",
        }
        for label, raw in fixtures.items():
            with self.subTest(label=label):
                result = self.parse(raw)
                self.assertNotEqual(result.parse_status, "parsed_safe")
                self.assertNotEqual(result.search_disposition, "safe_numeric")
                self.assertIsNone(result.gpa_min_tenths)
                self.assertIsNone(result.gpa_max_tenths)

    def test_historical_safe_pattern_fails_closed(self) -> None:
        result = self.parse("全体の学習成績の状況3.8以上。", fallback=True)
        self.assertEqual(result.parse_status, "historical_reference")
        self.assertEqual(result.numeric_safety_tier, "do_not_numeric")
        self.assertIsNone(result.gpa_min_tenths)

    def test_null_is_not_unknown_or_no(self) -> None:
        result = self.parse(None)
        self.assertEqual(result.parse_status, "not_applicable")
        self.assertEqual(result.gpa_condition_type, "not_applicable")
        self.assertIsNone(result.raw_value)

    def test_integer_tenths_query_parser_boundaries(self) -> None:
        self.assertEqual(
            {value: parse_gpa_tenths(value) for value in ("3.0", "3.5", "4.0", "4.5")},
            {"3.0": 30, "3.5": 35, "4.0": 40, "4.5": 45},
        )
        for invalid in ("-1", "3.85", "5.1", " 3.8", "3.8 ", "nan"):
            with self.subTest(invalid=invalid), self.assertRaises(GPAContractError):
                parse_gpa_tenths(invalid)


class GPACurrentSnapshotRegressionTests(unittest.TestCase):
    def test_current_6699_row_snapshot(self) -> None:
        parser = GPAParser(GPACrosswalk.load(REPO_ROOT / GPA_AUDIT_PATH))
        counts: Counter[str] = Counter()
        minima: list[int] = []
        path = REPO_ROOT / "data/canonical/unified/master.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                result = parser.parse(
                    row["gpa_requirement"] or None,
                    admission_year=int(row["admission_year"]),
                    information_year=(
                        int(row["information_year"])
                        if row["information_year"]
                        else None
                    ),
                    fallback_previous_year=(
                        1 if row["fallback_previous_year"] == "true" else 0
                    ),
                )
                counts[result.numeric_safety_tier] += 1
                if result.gpa_min_tenths is not None:
                    minima.append(result.gpa_min_tenths)
        self.assertEqual(
            counts,
            Counter(
                safe_numeric=1258,
                conditional_numeric=747,
                do_not_numeric=4694,
            ),
        )
        expected = {30: 72, 35: 499, 38: 763, 40: 1175, 45: 1258}
        self.assertEqual(
            {value: sum(minimum <= value for minimum in minima) for value in expected},
            expected,
        )


class GPAReadOnlySearchTests(unittest.TestCase):
    def test_conditional_raw_is_retained_but_not_evaluated(self) -> None:
        raw = "3.0以上、または所定資格等"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root, gpa_requirement=raw)
            result = SQLiteBuildPipeline(root).build()
            with closing(sqlite3.connect(result.database_path)) as connection:
                rows = connection.execute(
                    """
                    SELECT raw_value, parse_status, search_disposition,
                           gpa_min_tenths, gpa_max_tenths
                    FROM admission_search_gpa ORDER BY admission_rowid
                    """
                ).fetchall()
                groups = connection.execute(
                    "SELECT COUNT(*) FROM admission_search_gpa_rule_groups"
                ).fetchone()[0]
            self.assertEqual(
                rows,
                [(raw, "conditional_review", "review_required", None, None)] * 2,
            )
            self.assertEqual(groups, 0)

    def test_builder_integration_and_read_only_search(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root, gpa_requirement="3.5以上")
            result = SQLiteBuildPipeline(root).build()
            before_search = hashlib.sha256(result.database_path.read_bytes()).hexdigest()

            below = search_gpa(result.database_path, "3.4")
            matched = search_gpa(result.database_path, "3.5")
            self.assertEqual(below.total_matches, 0)
            self.assertEqual(matched.total_matches, 2)
            self.assertEqual(matched.meaning, GPA_RESULT_MEANING)
            self.assertTrue(all(row["gpa_min_tenths"] == 35 for row in matched.rows))

            output = io.StringIO()
            with redirect_stdout(output):
                status = search_main(
                    [
                        "3.5",
                        "--database",
                        str(result.database_path),
                        "--limit",
                        "1",
                    ]
                )
            self.assertEqual(status, 0)
            rendered = output.getvalue()
            self.assertIn(GPA_RESULT_MEANING, rendered)
            self.assertNotIn("出願可能", rendered)
            self.assertNotIn("出願資格を満たす", rendered)
            self.assertEqual(
                hashlib.sha256(result.database_path.read_bytes()).hexdigest(),
                before_search,
            )


if __name__ == "__main__":
    unittest.main()
