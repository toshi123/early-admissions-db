from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from early_admissions.search import main as search_main
from early_admissions.search_qa import QA_SPECS
from early_admissions.sqlite_builder import SQLiteBuildPipeline
from early_admissions.structured_search import (
    MULTI_VALUE_FIELDS,
    RESULT_COLUMNS,
    SearchCriteria,
    StructuredSearchError,
    compile_result_query,
    search_database,
)

from tests.test_sqlite_build import prepare_unified_fixture
from tests.test_validator import REPO_ROOT


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StructuredSearchFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        prepare_unified_fixture(cls.root, gpa_requirement="3.5以上")
        cls.database = SQLiteBuildPipeline(cls.root).build().database_path
        cls.database_hash = sha256(cls.database)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_different_fields_are_and_same_field_values_are_or(self) -> None:
        both = search_database(
            self.database,
            SearchCriteria(institution_type=("国立", "私立")),
            limit=20,
        )
        one = search_database(
            self.database,
            SearchCriteria(
                institution_type=("国立", "私立"),
                university=("kokkoritsu大学",),
                school_recommendation_required=("No",),
            ),
            limit=20,
        )
        self.assertEqual(both.summary.total_matched_rows, 2)
        self.assertEqual(one.summary.total_matched_rows, 1)
        self.assertEqual(one.rows[0]["source_dataset"], "kokkoritsu")

    def test_gpa_safe_review_and_all_semantics(self) -> None:
        matched = search_database(
            self.database,
            SearchCriteria(gpa_tenths=35, gpa_mode="safe"),
            limit=20,
        )
        below = search_database(
            self.database,
            SearchCriteria(gpa_tenths=34, gpa_mode="safe"),
            limit=20,
        )
        all_rows = search_database(
            self.database,
            SearchCriteria(gpa_tenths=34, gpa_mode="all"),
            limit=20,
        )
        self.assertEqual(matched.summary.total_matched_rows, 2)
        self.assertEqual(
            {row["gpa_derived_status"] for row in matched.rows}, {"safe match"}
        )
        self.assertEqual(below.summary.total_matched_rows, 0)
        self.assertEqual(all_rows.summary.total_matched_rows, 2)
        self.assertEqual(all_rows.summary.gpa_safe_match_rows, 0)
        self.assertEqual(all_rows.summary.gpa_safe_no_match_rows, 2)
        self.assertEqual(
            {row["gpa_derived_status"] for row in all_rows.rows},
            {"safe no match"},
        )

    def test_reviewed_grade_requirement_and_overall_gpa_filters(self) -> None:
        required = search_database(
            self.database,
            SearchCriteria(grade_requirement_status="required"),
            limit=20,
        )
        below = search_database(
            self.database,
            SearchCriteria(
                grade_requirement_status="required", overall_gpa_tenths=34
            ),
            limit=20,
        )
        matched = search_database(
            self.database,
            SearchCriteria(
                grade_requirement_status="required", overall_gpa_tenths=35
            ),
            limit=20,
        )
        self.assertEqual(required.summary.total_matched_rows, 2)
        self.assertEqual(below.summary.total_matched_rows, 0)
        self.assertEqual(matched.summary.total_matched_rows, 2)

    def test_cli_exposes_new_grade_filters_without_changing_old_gpa(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = search_main(
                [
                    "--database", str(self.database),
                    "--grade-requirement", "required",
                    "--overall-gpa", "3.5",
                    "--format", "tsv",
                ]
            )
        self.assertEqual(status, 0)
        self.assertIn("grade_requirement_status", stdout.getvalue().splitlines()[0])
        self.assertIn("total matched rows: 2", stderr.getvalue())

    def test_result_contains_all_contract_columns(self) -> None:
        result = search_database(self.database, SearchCriteria(), limit=1)
        self.assertEqual(tuple(result.rows[0]), RESULT_COLUMNS)
        self.assertIsNone(result.summary.gpa_safe_match_rows)
        self.assertEqual(result.summary.gpa_safe_numeric_rule_rows, 2)

    def test_user_values_are_bound_not_interpolated(self) -> None:
        attack = "東京都') OR 1=1 --"
        compiled = compile_result_query(
            SearchCriteria(prefecture=(attack,)), limit=10, offset=0
        )
        self.assertNotIn(attack, compiled.sql)
        self.assertIn(attack, compiled.parameters)
        result = search_database(
            self.database, SearchCriteria(prefecture=(attack,)), limit=10
        )
        self.assertEqual(result.summary.total_matched_rows, 0)

    def test_every_supported_filter_compiles_to_parameters(self) -> None:
        values = {field: (f"value-for-{field}",) for field in MULTI_VALUE_FIELDS}
        criteria = SearchCriteria(
            **values,
            academic_field_group=("engineering", "information"),
            academic_field_mapping_status=("multi",),
            stem_flag=True,
            gpa_tenths=38,
            gpa_mode="all",
        )
        compiled = compile_result_query(criteria, limit=5, offset=2)
        for value in values.values():
            self.assertIn(value[0], compiled.parameters)
            self.assertNotIn(value[0], compiled.sql)
        self.assertIn(1, compiled.parameters)
        self.assertIn(38, compiled.parameters)
        self.assertIn("engineering", compiled.parameters)
        self.assertIn("information", compiled.parameters)
        self.assertIn("multi", compiled.parameters)

    def test_group_or_raw_and_status_and_other_fields(self) -> None:
        group = search_database(
            self.database,
            SearchCriteria(
                academic_field_group=("engineering", "information"),
                academic_field_mapping_status=("multi",),
                institution_type=("国立",),
                gpa_tenths=35,
                gpa_mode="safe",
            ),
            limit=20,
        )
        self.assertEqual(group.summary.total_matched_rows, 1)
        self.assertEqual(group.rows[0]["academic_field"], "理工・情報")
        self.assertEqual(group.rows[0]["academic_field_mapping_status"], "multi")
        self.assertEqual(
            group.rows[0]["academic_field_groups"],
            "natural_sciences,engineering,information",
        )

        raw_difference = search_database(
            self.database,
            SearchCriteria(
                academic_field=("工学",),
                academic_field_group=("engineering",),
            ),
            limit=20,
        )
        self.assertEqual(raw_difference.summary.total_matched_rows, 0)

    def test_group_values_are_bound_and_unknown_group_is_rejected(self) -> None:
        attack = "engineering') OR 1=1 --"
        compiled = compile_result_query(
            SearchCriteria(academic_field_group=(attack,)), limit=10, offset=0
        )
        self.assertNotIn(attack, compiled.sql)
        self.assertIn(attack, compiled.parameters)
        with self.assertRaisesRegex(
            StructuredSearchError, "Unknown academic-field group"
        ):
            search_database(
                self.database,
                SearchCriteria(academic_field_group=(attack,)),
                limit=10,
            )

    def test_cli_accepts_academic_field_group_and_status(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = search_main(
                [
                    "--database",
                    str(self.database),
                    "--academic-field-group",
                    "engineering",
                    "information",
                    "--academic-field-mapping-status",
                    "multi",
                    "--format",
                    "tsv",
                    "--limit",
                    "1",
                ]
            )
        self.assertEqual(status, 0)
        self.assertIn("academic_field_groups", stdout.getvalue().splitlines()[0])
        self.assertIn("natural_sciences,engineering,information", stdout.getvalue())
        self.assertIn("total matched rows: 2", stderr.getvalue())

    def test_csv_export_has_full_values_and_summary_on_stderr(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = search_main(
                [
                    "--database",
                    str(self.database),
                    "--institution-type",
                    "国立",
                    "--format",
                    "csv",
                    "--limit",
                    "1",
                ]
            )
        self.assertEqual(status, 0)
        self.assertIn("gpa_requirement", stdout.getvalue().splitlines()[0])
        self.assertIn("3.5以上", stdout.getvalue())
        self.assertNotIn("Search summary", stdout.getvalue())
        self.assertIn("total matched rows: 1", stderr.getvalue())

    def test_search_does_not_change_database_bytes(self) -> None:
        search_database(
            self.database,
            SearchCriteria(gpa_tenths=35, gpa_mode="review"),
            limit=None,
        )
        self.assertEqual(sha256(self.database), self.database_hash)

    def test_invalid_programmatic_gpa_mode_is_rejected(self) -> None:
        with self.assertRaisesRegex(StructuredSearchError, "requires a GPA"):
            search_database(
                self.database, SearchCriteria(gpa_mode="review"), limit=1
            )

    def test_overall_gpa_requires_the_reviewed_grade_requirement_filter(self) -> None:
        with self.assertRaisesRegex(StructuredSearchError, "requires"):
            search_database(
                self.database, SearchCriteria(overall_gpa_tenths=38), limit=1
            )


class CurrentDatabaseSearchRegressionTests(unittest.TestCase):
    def test_current_gpa_modes_and_read_only_hash(self) -> None:
        database = (
            REPO_ROOT
            / "data/derived/sqlite/v0_2_candidate/early_admissions_2027.sqlite"
        )
        before = sha256(database)
        safe = search_database(
            database, SearchCriteria(gpa_tenths=38, gpa_mode="safe"), limit=0
        )
        review = search_database(
            database, SearchCriteria(gpa_tenths=38, gpa_mode="review"), limit=0
        )
        all_rows = search_database(
            database, SearchCriteria(gpa_tenths=38, gpa_mode="all"), limit=0
        )
        self.assertEqual(safe.summary.total_matched_rows, 763)
        self.assertEqual(review.summary.total_matched_rows, 1510)
        self.assertEqual(all_rows.summary.total_matched_rows, 6699)
        self.assertEqual(all_rows.summary.gpa_safe_match_rows, 763)
        self.assertEqual(all_rows.summary.gpa_safe_no_match_rows, 495)
        self.assertEqual(all_rows.summary.gpa_conditional_review_rows, 747)
        self.assertEqual(all_rows.summary.gpa_not_numerically_evaluable_rows, 4694)
        self.assertEqual(sha256(database), before)

    def test_current_grade_requirement_counts_and_rikkyo_boundary(self) -> None:
        database = REPO_ROOT / "data/derived/sqlite/v0_2_candidate/early_admissions_2027.sqlite"
        required = search_database(
            database,
            SearchCriteria(grade_requirement_status="required"),
            limit=0,
        )
        overall_38 = search_database(
            database,
            SearchCriteria(
                grade_requirement_status="required", overall_gpa_tenths=38
            ),
            limit=0,
        )
        self.assertEqual(required.summary.total_matched_rows, 2373)
        self.assertEqual(overall_38.summary.total_matched_rows, 871)

        base = {"university": ("立教大学",)}
        below = search_database(
            database,
            SearchCriteria(
                **base, grade_requirement_status="required", overall_gpa_tenths=37
            ),
            limit=None,
        )
        matched = search_database(
            database,
            SearchCriteria(
                **base, grade_requirement_status="required", overall_gpa_tenths=38
            ),
            limit=None,
        )
        strict = search_database(
            database,
            SearchCriteria(**base, gpa_tenths=38, gpa_mode="safe"),
            limit=None,
        )
        identity = "RIKKYO-2027-SCI-03"
        self.assertNotIn(identity, {row["record_id"] for row in below.rows})
        self.assertIn(identity, {row["record_id"] for row in matched.rows})
        self.assertNotIn(identity, {row["record_id"] for row in strict.rows})

    def test_representative_qa_set_has_required_coverage(self) -> None:
        self.assertEqual(len(QA_SPECS), 25)
        labels = {spec.label for spec in QA_SPECS}
        for expected in (
            "東京＋理系",
            "東京＋理系＋評定3.8",
            "東京＋理系＋評定3.8＋研究活動関連",
            "東京/神奈川＋併願可",
            "学校推薦型＋推薦必要",
            "共通テスト不要",
            "口頭試問あり",
            "プレゼンあり",
            "面接＋小論文",
            "GPA 3.5 strict-safe",
            "GPA 3.8 strict-safe",
            "GPA 4.0 strict-safe",
            "東京＋工学group",
            "東京＋情報group",
            "東京/神奈川＋工学OR情報group＋GPA 3.8",
            "医学group",
            "医歯薬group",
            "農学OR生命科学group",
            "要確認academic field",
        ):
            self.assertIn(expected, labels)


if __name__ == "__main__":
    unittest.main()
