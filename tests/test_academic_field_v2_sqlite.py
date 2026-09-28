from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from contextlib import redirect_stderr
from pathlib import Path

from early_admissions.academic_field_v2 import (
    ACADEMIC_FIELD_V2_FROZEN_SHA256,
    AcademicFieldV2Contract,
)
from early_admissions.sqlite_builder import SQLiteBuildError, SQLiteBuildPipeline
from early_admissions.search import build_parser, criteria_from_args
from early_admissions.structured_search import (
    AcademicFieldV2Branch,
    SearchCriteria,
    StructuredSearchError,
    compile_result_query,
    search_database,
)

from tests.test_sqlite_build import prepare_unified_fixture
from tests.test_validator import REPO_ROOT


class AcademicFieldV2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = AcademicFieldV2Contract.load(REPO_ROOT)

    def test_frozen_sha_and_taxonomy_load(self) -> None:
        for relative, expected in ACADEMIC_FIELD_V2_FROZEN_SHA256.items():
            actual = hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected)
        self.assertEqual(len(self.contract.broad_groups), 30)
        self.assertEqual(len(self.contract.subcategories), 89)
        self.assertEqual(len(self.contract.raw_mappings), 489)
        self.assertEqual(len(self.contract.context_mappings), 789)

    def test_exact_raw_multi_and_no_substring_inference(self) -> None:
        multi = self.contract.classify(
            source_dataset="kokkoritsu",
            university="fixture大学",
            faculty_school=None,
            department=None,
            academic_field="理工・情報",
        )
        self.assertEqual(multi.broad_mapping_status, "multi")
        self.assertEqual(
            tuple(value[0] for value in multi.broad_memberships),
            ("natural_sciences", "engineering", "information"),
        )
        unknown = self.contract.classify(
            source_dataset="kokkoritsu",
            university="fixture大学",
            faculty_school="理学部",
            department="理学療法推測学科",
            academic_field="理学療法X",
        )
        self.assertEqual(unknown.broad_mapping_status, "unmapped")
        self.assertEqual(unknown.broad_memberships, ())

    def test_context_additive_is_exact_and_preserves_raw(self) -> None:
        exact = self.contract.classify(
            source_dataset="kokkoritsu",
            university="お茶の水女子大学",
            faculty_school="理学部",
            department="化学科",
            academic_field="理学",
        )
        self.assertEqual(exact.context_mapping_effect, "additive")
        self.assertEqual(
            exact.broad_memberships,
            (("natural_sciences", "raw_and_context"),),
        )
        self.assertEqual(
            exact.subcategory_memberships,
            (("chemistry", "natural_sciences", "context_exact"),),
        )
        non_exact = self.contract.classify(
            source_dataset="kokkoritsu",
            university="お茶の水女子大学",
            faculty_school="理学部",
            department="化学科 ",
            academic_field="理学",
        )
        self.assertEqual(non_exact.context_mapping_consulted, 0)
        self.assertEqual(non_exact.subcategory_mapping_status, "none")

    def test_context_authoritative_and_unresolved_review(self) -> None:
        resolved = self.contract.classify(
            source_dataset="kokkoritsu",
            university="宇都宮大学",
            faculty_school="地域デザイン科学部",
            department="コミュニティデザイン学科",
            academic_field="地域デザイン",
        )
        self.assertEqual(resolved.context_mapping_effect, "authoritative")
        self.assertEqual(
            resolved.broad_memberships,
            (("sociology_community", "context_exact"),),
        )
        unresolved = self.contract.classify(
            source_dataset="shidai",
            university="千葉科学大学",
            faculty_school="危機管理学部",
            department="航空技術危機管理学科 パイロットコース",
            academic_field="航空・パイロット",
        )
        self.assertEqual(unresolved.context_mapping_consulted, 1)
        self.assertEqual(unresolved.context_mapping_effect, "none")
        self.assertEqual(unresolved.broad_mapping_status, "review_required")
        self.assertEqual(unresolved.broad_memberships, ())

    def test_important_ambiguous_and_domain_negative_cases(self) -> None:
        cases = (
            ("人間科学", "review_required", (), ()),
            ("航空・パイロット", "review_required", (), ()),
            (
                "理学療法",
                "single",
                ("nursing_health",),
                ("physical_therapy",),
            ),
            (
                "言語聴覚",
                "single",
                ("nursing_health",),
                ("speech_hearing",),
            ),
            ("獣医学", "single", ("veterinary",), ("veterinary_medicine",)),
        )
        for raw, status, broad, subcategories in cases:
            with self.subTest(raw=raw):
                result = self.contract.classify(
                    source_dataset="kokkoritsu",
                    university="fixture大学",
                    faculty_school=None,
                    department=None,
                    academic_field=raw,
                )
                self.assertEqual(result.broad_mapping_status, status)
                self.assertEqual(
                    tuple(value[0] for value in result.broad_memberships), broad
                )
                self.assertEqual(
                    tuple(value[0] for value in result.subcategory_memberships),
                    subcategories,
                )


class AcademicFieldV2SQLiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        prepare_unified_fixture(cls.root)
        cls.result = SQLiteBuildPipeline(cls.root).build()
        cls.database = cls.result.database_path

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_parent_taxonomy_membership_and_raw_integrity(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM academic_field_v2_broad_taxonomy"
                ).fetchone()[0],
                30,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM academic_field_v2_subcategory_taxonomy"
                ).fetchone()[0],
                89,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM admission_search_academic_fields_v2"
                ).fetchone()[0],
                2,
            )
            statuses = connection.execute(
                """
                SELECT broad_mapping_status, subcategory_mapping_status,
                       context_mapping_consulted, context_mapping_effect
                FROM admission_search_academic_fields_v2
                ORDER BY admission_rowid
                """
            ).fetchall()
            self.assertEqual(statuses, [("multi", "none", 0, "none")] * 2)
            broad = connection.execute(
                """
                SELECT admission_rowid, group_code, membership_order, mapping_basis
                FROM admission_search_academic_field_broad_memberships_v2
                ORDER BY admission_rowid, membership_order
                """
            ).fetchall()
            self.assertEqual(
                broad,
                [
                    (1, "natural_sciences", 1, "raw_exact"),
                    (1, "engineering", 2, "raw_exact"),
                    (1, "information", 3, "raw_exact"),
                    (2, "natural_sciences", 1, "raw_exact"),
                    (2, "engineering", 2, "raw_exact"),
                    (2, "information", 3, "raw_exact"),
                ],
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM admissions AS a
                    JOIN admission_search_academic_fields_v2 AS p
                      USING (admission_rowid)
                    WHERE NOT (a.academic_field IS p.raw_value)
                    """
                ).fetchone()[0],
                0,
            )
            zero_count = connection.execute(
                """
                SELECT COUNT(*) FROM academic_field_v2_subcategory_taxonomy AS t
                LEFT JOIN admission_search_academic_field_subcategory_memberships_v2 AS m
                  USING (subcategory_code)
                GROUP BY t.subcategory_code HAVING COUNT(m.admission_rowid) = 0
                """
            ).fetchall()
            self.assertTrue(zero_count)

    def test_subcategory_requires_same_admission_parent_broad(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO
                      admission_search_academic_field_subcategory_memberships_v2
                      (admission_rowid, subcategory_code, parent_group_code,
                       membership_order, mapping_basis)
                    VALUES (
                        1, 'law', 'law_politics_policy', 1, 'raw_exact'
                    )
                    """
                )

    def test_broad_subcategory_and_multi_branch_semantics(self) -> None:
        broad = search_database(
            self.database,
            SearchCriteria(
                academic_field_v2_branches=(
                    AcademicFieldV2Branch("natural_sciences"),
                )
            ),
            limit=20,
        )
        child_only = search_database(
            self.database,
            SearchCriteria(
                academic_field_v2_branches=(
                    AcademicFieldV2Branch(
                        "natural_sciences", ("mathematics_statistics",)
                    ),
                )
            ),
            limit=20,
        )
        branches = search_database(
            self.database,
            SearchCriteria(
                academic_field_v2_branches=(
                    AcademicFieldV2Branch(
                        "natural_sciences", ("mathematics_statistics",)
                    ),
                    AcademicFieldV2Branch("engineering"),
                )
            ),
            limit=20,
        )
        self.assertEqual(broad.summary.total_matched_rows, 2)
        self.assertEqual(child_only.summary.total_matched_rows, 0)
        self.assertEqual(branches.summary.total_matched_rows, 2)

    def test_parent_mismatch_and_unknown_are_rejected(self) -> None:
        with self.assertRaisesRegex(StructuredSearchError, "parent mismatch"):
            search_database(
                self.database,
                SearchCriteria(
                    academic_field_v2_branches=(
                        AcademicFieldV2Branch("engineering", ("physics",)),
                    )
                ),
            )

    def test_cli_branch_contract_and_missing_parent_rejection(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--academic-field-v2",
                "natural_sciences",
                "engineering",
                "--academic-subfield-v2",
                "natural_sciences=mathematics_statistics,physics",
            ]
        )
        criteria = criteria_from_args(args, parser)
        self.assertEqual(
            criteria.academic_field_v2_branches,
            (
                AcademicFieldV2Branch(
                    "natural_sciences", ("mathematics_statistics", "physics")
                ),
                AcademicFieldV2Branch("engineering"),
            ),
        )
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            bad_args = parser.parse_args(
                [
                    "--academic-field-v2",
                    "engineering",
                    "--academic-subfield-v2",
                    "natural_sciences=physics",
                ]
            )
            criteria_from_args(bad_args, parser)
        with self.assertRaisesRegex(StructuredSearchError, "Unknown.*broad"):
            search_database(
                self.database,
                SearchCriteria(
                    academic_field_v2_branches=(
                        AcademicFieldV2Branch("engineering_guess"),
                    )
                ),
            )

    def test_values_are_bound_and_v0_1_coexists_by_and(self) -> None:
        attack = "engineering') OR 1=1 --"
        compiled = compile_result_query(
            SearchCriteria(
                academic_field_v2_branches=(AcademicFieldV2Branch(attack),)
            ),
            limit=5,
            offset=0,
        )
        self.assertNotIn(attack, compiled.sql)
        self.assertIn(attack, compiled.parameters)
        coexistence = search_database(
            self.database,
            SearchCriteria(
                academic_field_group=("engineering",),
                academic_field_v2_branches=(
                    AcademicFieldV2Branch("natural_sciences"),
                ),
            ),
            limit=20,
        )
        self.assertEqual(coexistence.summary.total_matched_rows, 2)

    def test_validation_receipt_and_manifest(self) -> None:
        validation = self.result.validation["academic_field_v2"]
        self.assertEqual(validation["status"], "passed")
        self.assertEqual(validation["missing_subcategory_parent_broad"], 0)
        self.assertEqual(validation["raw_mismatch_rows"], 0)

    def test_builder_loads_exact_additive_and_authoritative_contexts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(
                root,
                master_overrides_by_dataset={
                    "kokkoritsu": {
                        "university": "宇都宮大学",
                        "faculty_school": "地域デザイン科学部",
                        "department": "コミュニティデザイン学科",
                        "academic_field": "地域デザイン",
                    },
                    "shidai": {
                        "university": "創価大学",
                        "faculty_school": "理工学部",
                        "department": "情報システム工学科",
                        "academic_field": "情報・工学",
                    },
                },
            )
            result = SQLiteBuildPipeline(root).build()
            with closing(sqlite3.connect(result.database_path)) as connection:
                parents = connection.execute(
                    """
                    SELECT a.source_dataset, p.context_mapping_consulted,
                           p.context_mapping_effect, p.broad_mapping_status,
                           p.subcategory_mapping_status
                    FROM admissions AS a
                    JOIN admission_search_academic_fields_v2 AS p
                      USING (admission_rowid)
                    ORDER BY a.source_dataset
                    """
                ).fetchall()
                memberships = connection.execute(
                    """
                    SELECT a.source_dataset, s.subcategory_code,
                           s.parent_group_code, s.mapping_basis
                    FROM admissions AS a
                    JOIN
                      admission_search_academic_field_subcategory_memberships_v2
                      AS s USING (admission_rowid)
                    ORDER BY a.source_dataset
                    """
                ).fetchall()
            self.assertEqual(
                parents,
                [
                    ("kokkoritsu", 1, "authoritative", "single", "single"),
                    ("shidai", 1, "additive", "multi", "single"),
                ],
            )
            self.assertEqual(
                memberships,
                [
                    (
                        "kokkoritsu",
                        "community_regional_society",
                        "sociology_community",
                        "context_exact",
                    ),
                    ("shidai", "software_systems", "information", "context_exact"),
                ],
            )

    def test_logical_rebuild_is_deterministic(self) -> None:
        second = SQLiteBuildPipeline(
            self.root, output_dir="data/derived/sqlite-second"
        ).build()
        tables = (
            "academic_field_v2_broad_taxonomy",
            "academic_field_v2_subcategory_taxonomy",
            "admission_search_academic_fields_v2",
            "admission_search_academic_field_broad_memberships_v2",
            "admission_search_academic_field_subcategory_memberships_v2",
        )
        with closing(sqlite3.connect(self.database)) as first_connection, closing(
            sqlite3.connect(second.database_path)
        ) as second_connection:
            for table in tables:
                with self.subTest(table=table):
                    first_rows = first_connection.execute(
                        f"SELECT * FROM {table} ORDER BY 1, 2"
                    ).fetchall()
                    second_rows = second_connection.execute(
                        f"SELECT * FROM {table} ORDER BY 1, 2"
                    ).fetchall()
                    self.assertEqual(first_rows, second_rows)

    def test_v2_freeze_sha_mismatch_fails_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            crosswalk = root / next(
                path
                for path in ACADEMIC_FIELD_V2_FROZEN_SHA256
                if "raw_crosswalk" in path.name
            )
            crosswalk.write_bytes(crosswalk.read_bytes() + b"\n")
            pipeline = SQLiteBuildPipeline(root)
            with self.assertRaisesRegex(
                SQLiteBuildError, "Frozen academic-field v0.2 SHA-256 mismatch"
            ):
                pipeline.build()
            self.assertFalse(pipeline.database_path.exists())


class CurrentAcademicFieldV2SQLiteRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database = (
            REPO_ROOT / "data/derived/sqlite/v0_2_candidate/early_admissions_2027.sqlite"
        )
        cls.manifest = json.loads(
            (REPO_ROOT / "data/derived/sqlite/v0_2_candidate/build_manifest.json").read_text(
                encoding="utf-8"
            )
        )

    def test_current_snapshot_counts(self) -> None:
        layer = self.manifest["academic_field_v2"]
        self.assertEqual(layer["broad_taxonomy_rows"], 30)
        self.assertEqual(layer["subcategory_taxonomy_rows"], 89)
        self.assertEqual(layer["parent_rows"], 6592)
        self.assertEqual(layer["raw_crosswalk_keys"], 487)
        self.assertEqual(layer["raw_crosswalk_rows"], 860)
        self.assertEqual(layer["context_crosswalk_tuples"], 789)
        self.assertEqual(layer["context_crosswalk_rows"], 941)
        self.assertEqual(layer["raw_only_mapping_admissions"], 4999)
        self.assertEqual(layer["context_consulted_admissions"], 1593)
        self.assertEqual(layer["context_effect_admissions"], 1582)
        self.assertEqual(
            layer["broad_mapping_status_counts"],
            {
                "single": 4377,
                "multi": 2199,
                "review_required": 11,
                "unmapped": 5,
                "not_applicable": 0,
            },
        )
        self.assertEqual(
            layer["subcategory_mapping_status_counts"],
            {
                "single": 3809,
                "multi": 1675,
                "none": 1092,
                "review_required": 11,
                "unmapped": 5,
                "not_applicable": 0,
            },
        )
        self.assertEqual(layer["raw_mismatch_rows"], 0)
        self.assertEqual(layer["validation_status"], "passed")

    def test_representative_candidate_queries(self) -> None:
        for group_code, expected in (
            ("law_politics_policy", 117),
            ("economics", 174),
            ("business_commerce", 194),
            ("psychology", 32),
            ("languages", 198),
            ("natural_sciences", 770),
            ("engineering", 1709),
            ("information", 899),
        ):
            with self.subTest(group_code=group_code):
                result = search_database(
                    self.database,
                    SearchCriteria(
                        academic_field_v2_branches=(
                            AcademicFieldV2Branch(group_code),
                        )
                    ),
                    limit=0,
                )
                self.assertEqual(result.summary.total_matched_rows, expected)
        for group_code, subcategory, expected in (
            ("law_politics_policy", "law", 74),
            ("economics", "economics_general", 170),
            ("business_commerce", "management", 186),
            ("psychology", "psychology_general", 26),
            ("natural_sciences", "mathematics_statistics", 114),
            ("natural_sciences", "physics", 94),
            ("engineering", "mechanical", 337),
            ("nursing_health", "nursing", 286),
        ):
            with self.subTest(subcategory=subcategory):
                result = search_database(
                    self.database,
                    SearchCriteria(
                        academic_field_v2_branches=(
                            AcademicFieldV2Branch(group_code, (subcategory,)),
                        )
                    ),
                    limit=0,
                )
                self.assertEqual(result.summary.total_matched_rows, expected)

    def test_all_89_subcategory_counts_match_manifest(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            counts = {
                row[0]: row[1]
                for row in connection.execute(
                    """
                    SELECT t.subcategory_code, COUNT(m.admission_rowid)
                    FROM academic_field_v2_subcategory_taxonomy AS t
                    LEFT JOIN
                      admission_search_academic_field_subcategory_memberships_v2 AS m
                      USING (subcategory_code)
                    GROUP BY t.subcategory_code, t.rowid ORDER BY t.rowid
                    """
                )
            }
        self.assertEqual(len(counts), 89)
        self.assertEqual(
            counts,
            self.manifest["academic_field_v2"]["subcategory_membership_counts"],
        )


if __name__ == "__main__":
    unittest.main()
