from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from early_admissions.build_site_data import build_parser as site_build_parser
from early_admissions.build_sqlite import build_parser as sqlite_build_parser
from early_admissions.site_data_builder import SiteDataBuildPipeline
from early_admissions.site_search import SearchRequest, load_search_rows, search_rows
from early_admissions.sqlite_builder import SQLiteBuildError, SQLiteBuildPipeline

from tests.test_sqlite_build import prepare_unified_fixture, refresh_unified_manifest
from tests.test_validator import REPO_ROOT, write_csv


UNMAPPED_ENGLISH = "監査前の新規英語資格条件"


def prepare_profile_fixture(root: Path, **kwargs: object) -> None:
    prepare_unified_fixture(root, **kwargs)
    shutil.copytree(REPO_ROOT / "schema/site", root / "schema/site")


class ValidationProfileTests(unittest.TestCase):
    def test_default_and_explicit_production_reject_english_unmapped(self) -> None:
        for profile in (None, "production"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prepare_profile_fixture(
                    root,
                    master_overrides_by_dataset={
                        "kokkoritsu": {"english_requirement": UNMAPPED_ENGLISH}
                    },
                )
                kwargs = {} if profile is None else {"validation_profile": profile}
                with self.assertRaisesRegex(
                    SQLiteBuildError, "production profile prohibits 1 unmapped"
                ):
                    SQLiteBuildPipeline(root, **kwargs).build()

    def test_candidate_audit_preserves_raw_excludes_binary_filters_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_profile_fixture(
                root,
                master_overrides_by_dataset={
                    "kokkoritsu": {"english_requirement": UNMAPPED_ENGLISH}
                },
            )
            sqlite_result = SQLiteBuildPipeline(
                root, validation_profile="candidate-audit"
            ).build()
            manifest = json.loads(
                sqlite_result.manifest_path.read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["validation_profile"], "candidate_audit")
            self.assertFalse(manifest["publication"]["production_ready"])
            self.assertEqual(manifest["row_counts"]["admissions"], 2)
            self.assertEqual(
                manifest["review_required_counts"]["english_unmapped_admissions"],
                1,
            )
            with closing(sqlite3.connect(sqlite_result.database_path)) as connection:
                row = connection.execute(
                    """
                    SELECT raw_value, requirement_status, parse_status,
                           search_disposition
                    FROM admission_search_english_requirement
                    WHERE raw_value = ?
                    """,
                    (UNMAPPED_ENGLISH,),
                ).fetchone()
                self.assertEqual(
                    row,
                    (
                        UNMAPPED_ENGLISH,
                        "unmapped",
                        "unmapped",
                        "review_required",
                    ),
                )
                self.assertEqual(
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM admission_search_english_requirement_safe
                        WHERE raw_value = ?
                        """,
                        (UNMAPPED_ENGLISH,),
                    ).fetchone()[0],
                    0,
                )

            site_result = SiteDataBuildPipeline(
                root,
                validation_profile="candidate-audit",
                build_timestamp_utc="2026-09-22T00:00:00Z",
            ).build()
            rows = load_search_rows(site_result.output_dir)
            self.assertEqual(len(rows), 2)
            candidate = next(
                row for row in rows if row["english_requirement"] == UNMAPPED_ENGLISH
            )
            self.assertEqual(candidate["english_requirement_status"], "unmapped")
            for status in ("required", "not_required"):
                matched = search_rows(
                    rows,
                    SearchRequest(english_requirement_status=(status,)),
                    limit=None,
                ).rows
                self.assertNotIn(candidate, matched)
            site_manifest = json.loads(
                site_result.manifest_path.read_text(encoding="utf-8")
            )
            self.assertEqual(site_manifest["counts"]["search_rows"], 2)
            self.assertEqual(site_manifest["counts"]["detail_records"], 2)
            self.assertFalse(site_manifest["publication"]["production_ready"])

    def test_candidate_gpa_and_grade_unmapped_remain_non_numeric(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = "監査前の新規評定条件 3.9"
            prepare_profile_fixture(root, gpa_requirement=raw)
            result = SQLiteBuildPipeline(
                root,
                validation_profile="candidate-audit",
                audit_review_counts={"gpa_new_unmapped_admissions": 2},
            ).build()
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["review_required_counts"]["gpa_new_unmapped_admissions"],
                2,
            )
            self.assertEqual(
                manifest["review_required_counts"]["gpa_unparsed_admissions"], 2
            )
            with closing(sqlite3.connect(result.database_path)) as connection:
                rows = connection.execute(
                    """
                    SELECT g.raw_value, g.parse_status, g.gpa_min_tenths,
                           r.grade_requirement_status,
                           r.overall_gpa_min_tenths, r.overall_gpa_status
                    FROM admission_search_gpa AS g
                    JOIN admission_search_grade_requirements AS r
                      USING (admission_rowid)
                    ORDER BY g.admission_rowid
                    """
                ).fetchall()
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(row[0], raw)
                self.assertEqual(row[1], "unparsed")
                self.assertIsNone(row[2])
                self.assertEqual(row[3], "unmapped")
                self.assertIsNone(row[4])
                self.assertEqual(row[5], "unmapped")

    def test_candidate_academic_unmapped_has_no_guessed_memberships(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_profile_fixture(root, academic_field="未監査の学問分野")
            result = SQLiteBuildPipeline(
                root, validation_profile="candidate-audit"
            ).build()
            with closing(sqlite3.connect(result.database_path)) as connection:
                parents = connection.execute(
                    """
                    SELECT mapping_status, broad_mapping_status,
                           subcategory_mapping_status
                    FROM admission_search_academic_fields
                    JOIN admission_search_academic_fields_v2 USING (admission_rowid)
                    ORDER BY admission_rowid
                    """
                ).fetchall()
                memberships = sum(
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in (
                        "admission_search_academic_field_groups",
                        "admission_search_academic_field_broad_memberships_v2",
                        "admission_search_academic_field_subcategory_memberships_v2",
                    )
                )
            self.assertTrue(all(row == ("unmapped", "unmapped", "unmapped") for row in parents))
            self.assertEqual(memberships, 0)

    def test_fk_and_invalid_tristate_remain_hard_errors_in_both_profiles(self) -> None:
        for profile in ("production", "candidate-audit"):
            with self.subTest(kind="fk", profile=profile), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prepare_profile_fixture(root)
                path = root / "data/canonical/unified/research_requirements.csv"
                with path.open("r", encoding="utf-8", newline="") as handle:
                    header = next(csv.reader(handle))
                row = {field: "" for field in header}
                row.update(
                    {
                        "source_dataset": "kokkoritsu",
                        "source_version": "5.61",
                        "admission_id": "MISSING",
                        "university": "不存在大学",
                        "source_url": "https://example.test/orphan",
                        "verified_on": "2026-09-22",
                    }
                )
                write_csv(path, header, [row])
                refresh_unified_manifest(root)
                with self.assertRaises(SQLiteBuildError):
                    SQLiteBuildPipeline(root, validation_profile=profile).build()

    def test_malformed_sql_schema_remains_a_hard_error_in_both_profiles(self) -> None:
        for profile in ("production", "candidate-audit"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prepare_profile_fixture(root)
                schema = root / "schema/sqlite/early_admissions_sqlite_schema_v0_1.sql"
                schema.write_text("THIS IS NOT SQL;\n", encoding="utf-8")
                with self.assertRaises(SQLiteBuildError):
                    SQLiteBuildPipeline(root, validation_profile=profile).build()

            with self.subTest(kind="tristate", profile=profile), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prepare_profile_fixture(root)
                path = root / "data/canonical/unified/master.csv"
                with path.open("r", encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                    header = list(rows[0])
                rows[0]["selection_interview"] = "Maybe"
                write_csv(path, header, rows)
                refresh_unified_manifest(root)
                with self.assertRaises(SQLiteBuildError):
                    SQLiteBuildPipeline(root, validation_profile=profile).build()

    def test_candidate_site_requires_explicit_matching_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_profile_fixture(
                root,
                master_overrides_by_dataset={
                    "kokkoritsu": {"english_requirement": UNMAPPED_ENGLISH}
                },
            )
            SQLiteBuildPipeline(root, validation_profile="candidate-audit").build()
            with self.assertRaisesRegex(Exception, "profile"):
                SiteDataBuildPipeline(root).build()

    def test_cli_defaults_are_production_and_candidate_is_explicit(self) -> None:
        self.assertEqual(
            sqlite_build_parser().parse_args([]).validation_profile, "production"
        )
        self.assertEqual(
            site_build_parser().parse_args([]).validation_profile, "production"
        )
        self.assertEqual(
            sqlite_build_parser()
            .parse_args(["--validation-profile", "candidate-audit"])
            .validation_profile,
            "candidate-audit",
        )


if __name__ == "__main__":
    unittest.main()
