from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from typing import Mapping

from early_admissions.sqlite_builder import (
    DATABASE_FILENAME,
    SQLiteBuildError,
    SQLiteBuildPipeline,
    SQLiteCapabilities,
)
from early_admissions.unified_builder import UnifiedBuildPipeline

from tests.test_validator import REPO_ROOT, build_synthetic_repo, write_csv


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_unified_fixture(
    root: Path,
    *,
    duplicate_children: bool = False,
    gpa_requirement: str | None = None,
    academic_field: str | None = "理工・情報",
    master_overrides_by_dataset: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, dict[str, object]]:
    states = build_synthetic_repo(root)
    for relative in (
        Path("docs/sqlite_design_v0_1.md"),
        Path("docs/gpa_search_design_v0_1.md"),
        Path("schema/sqlite/early_admissions_sqlite_schema_v0_1.sql"),
        Path("schema/sqlite/admission_search_gpa_schema_v0_1.sql"),
        Path("docs/grade_requirement_search_design_v0_1.md"),
        Path("schema/sqlite/admission_search_grade_requirement_schema_v0_1.sql"),
        Path("schema/grade_requirement/grade_requirement_crosswalk_v0_2.csv"),
        Path("schema/sqlite/admission_search_academic_field_schema_v0_1.sql"),
        Path("schema/academic_field/academic_field_taxonomy_v0_1.csv"),
        Path("schema/academic_field/academic_field_crosswalk_v0_2.csv"),
        Path("validation/reports/gpa_requirement_raw_value_audit_v0_2.csv"),
        Path("docs/academic_field_search_design_v0_1.md"),
        Path("docs/academic_field_mapping_freeze_v0_1.md"),
        Path("docs/academic_field_v0_2_sqlite_design.md"),
        Path("docs/academic_field_crosswalk_v0_3.md"),
        Path("docs/academic_field_taxonomy_v0_2_freeze.md"),
        Path("validation/reports/academic_field_taxonomy_v0_2_audit.md"),
        Path("schema/sqlite/admission_search_academic_field_v0_2_schema.sql"),
        Path(
            "schema/academic_field/v0_2/"
            "academic_field_broad_taxonomy_v0_2.csv"
        ),
        Path(
            "schema/academic_field/v0_2/"
            "academic_field_subcategory_taxonomy_v0_2.csv"
        ),
        Path(
            "schema/academic_field/v0_3/"
            "academic_field_raw_crosswalk_v0_3.csv"
        ),
        Path(
            "schema/academic_field/v0_3/"
            "academic_field_context_crosswalk_v0_3.csv"
        ),
        Path(
            "schema/academic_field/v0_2/"
            "academic_field_v0_1_to_v0_2_crosswalk.csv"
        ),
        Path("docs/english_requirement_search_design_v0_1.md"),
        Path("docs/english_requirement_crosswalk_v0_2.md"),
        Path("schema/sqlite/admission_search_english_requirement_schema_v0_1.sql"),
        Path("schema/english_requirement/english_requirement_crosswalk_v0_2.csv"),
        Path("docs/prefecture_search_design_v0_1.md"),
        Path("schema/sqlite/admission_search_prefecture_schema_v0_1.sql"),
        Path("schema/prefecture/prefecture_taxonomy_v0_1.csv"),
        Path("schema/prefecture/prefecture_crosswalk_v0_1.csv"),
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)
    if (
        gpa_requirement is not None
        or academic_field is not None
        or master_overrides_by_dataset
    ):
        for dataset, state in states.items():
            if gpa_requirement is not None:
                state["master"]["gpa_requirement"] = gpa_requirement
            if academic_field is not None:
                state["master"]["academic_field"] = academic_field
            if master_overrides_by_dataset:
                state["master"].update(
                    master_overrides_by_dataset.get(dataset, {})
                )
                if "university" in master_overrides_by_dataset.get(dataset, {}):
                    state["coverage"]["university"] = state["master"][
                        "university"
                    ]
                    write_csv(
                        state["canonical"] / "coverage.csv",
                        state["coverage_header"],
                        [state["coverage"]],
                    )
            write_csv(
                state["canonical"] / "master.csv",
                state["master_header"],
                [state["master"]],
            )
    if duplicate_children:
        state = states["kokkoritsu"]
        research = {field: "" for field in state["research_header"]}
        research.update(
            {
                "admission_id": "KOKKORITSU-1",
                "university": "kokkoritsu大学",
                "requirement_code": "fixture-detail",
                "requirement_detail": "exact duplicate retained",
                "source_url": "https://example.test/research",
                "verified_on": "2026-09-20",
            }
        )
        write_csv(
            state["canonical"] / "research_requirements.csv",
            state["research_header"],
            [research, research],
        )
    UnifiedBuildPipeline(root).build()
    return states


def refresh_unified_manifest(root: Path) -> None:
    unified = root / "data/canonical/unified"
    manifest_path = unified / "build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    hashes: dict[str, str] = {}
    for table in ("master", "coverage", "research_requirements"):
        path = unified / f"{table}.csv"
        raw = path.read_bytes()
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            rows = list(reader)
        metadata = manifest["outputs"][table]
        metadata.update(
            {
                "rows": len(rows),
                "columns": len(header),
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        counts[table] = len(rows)
        hashes[table] = metadata["sha256"]
    validation = manifest["validation"]
    preservation = validation["unified"]["row_preservation"]
    preservation["expected_output_rows"] = counts
    preservation["input_rows"] = counts
    preservation["output_rows"] = counts
    validation["unified"]["json_schema"]["validated_rows"] = counts
    validation["determinism"]["sha256"] = hashes
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )


class SQLiteBuildPipelineTests(unittest.TestCase):
    def test_successful_build_and_query_plan_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)

            result = SQLiteBuildPipeline(
                root, build_timestamp_utc="2026-09-22T11:38:21Z"
            ).build()
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

            self.assertTrue(result.database_path.is_file())
            self.assertEqual(
                manifest["build_timestamp_utc"], "2026-09-22T11:38:21Z"
            )
            self.assertEqual(
                result.row_counts,
                {"admissions": 2, "coverage": 2, "research_requirements": 0},
            )
            self.assertEqual(manifest["validation"]["status"], "passed")
            self.assertEqual(
                len(
                    manifest["validation"]["structured_query_smoke_tests"][
                        "queries"
                    ]
                ),
                8,
            )
            self.assertEqual(manifest["output"]["sha256"], sha256(result.database_path))
            self.assertFalse(Path(str(result.database_path) + "-wal").exists())
            self.assertFalse(Path(str(result.database_path) + "-shm").exists())
            with closing(sqlite3.connect(result.database_path)) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM admissions_search")
                    .fetchone()[0],
                    2,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM admission_search_dates")
                    .fetchone()[0],
                    0,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM admission_search_gpa")
                    .fetchone()[0],
                    2,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM admission_search_grade_requirements"
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM admission_search_gpa_rule_groups"
                    ).fetchone()[0],
                    0,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM admission_search_academic_fields"
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM admission_search_academic_field_groups"
                    ).fetchone()[0],
                    6,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM academic_field_taxonomy"
                    ).fetchone()[0],
                    19,
                )
            self.assertEqual(
                manifest["gpa_search"]["classification_counts"],
                {
                    "safe_numeric": 0,
                    "conditional_numeric": 0,
                    "do_not_numeric": 2,
                },
            )
            self.assertEqual(
                manifest["grade_requirement_search"]["classification_counts"],
                {
                    "required": 0,
                    "not_required": 0,
                    "review_required": 0,
                    "unknown": 2,
                    "not_applicable": 0,
                    "unmapped": 0,
                },
            )
            self.assertEqual(
                manifest["validation"]["grade_requirement_search"][
                    "raw_mismatch_rows"
                ],
                0,
            )
            self.assertEqual(
                manifest["academic_field_search"]["classification_counts"],
                {
                    "single": 0,
                    "multi": 2,
                    "review_required": 0,
                    "unmapped": 0,
                    "not_applicable": 0,
                },
            )
            self.assertEqual(
                manifest["validation"]["academic_field_search"][
                    "raw_value_mismatches"
                ],
                0,
            )

    def test_null_boolean_and_tristate_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            result = SQLiteBuildPipeline(root).build()

            with closing(sqlite3.connect(result.database_path)) as connection:
                row = connection.execute(
                    """
                    SELECT prefecture, typeof(prefecture), stem_flag,
                           typeof(stem_flag), fallback_previous_year,
                           typeof(fallback_previous_year),
                           school_recommendation_required,
                           academic_record_required,
                           typeof(academic_record_required)
                    FROM admissions WHERE source_dataset = 'kokkoritsu'
                    """
                ).fetchone()
            self.assertIsNone(row[0])
            self.assertEqual(row[1], "null")
            self.assertEqual((row[2], row[3]), (1, "integer"))
            self.assertEqual((row[4], row[5]), (0, "integer"))
            self.assertEqual(row[6], "No")
            self.assertEqual((row[7], row[8]), ("Unknown", "text"))

    def test_exact_duplicate_children_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root, duplicate_children=True)
            result = SQLiteBuildPipeline(root).build()

            with closing(sqlite3.connect(result.database_path)) as connection:
                rows = connection.execute(
                    "SELECT * FROM research_requirements ORDER BY research_rowid"
                ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertNotEqual(rows[0][0], rows[1][0])
            self.assertEqual(rows[0][1:], rows[1][1:])
            duplicate = result.validation["research_duplicate_preservation"]
            self.assertEqual(duplicate["input_exact_duplicate_excess_rows"], 1)
            self.assertEqual(duplicate["database_exact_duplicate_excess_rows"], 1)

    def test_orphan_fk_fails_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            path = root / "data/canonical/unified/research_requirements.csv"
            with path.open("r", encoding="utf-8", newline="") as handle:
                header = next(csv.reader(handle))
            orphan = {field: "" for field in header}
            orphan.update(
                {
                    "source_dataset": "kokkoritsu",
                    "source_version": "5.81",
                    "admission_id": "MISSING-1",
                    "university": "不存在大学",
                    "source_url": "https://example.test/orphan",
                    "verified_on": "2026-09-20",
                }
            )
            write_csv(path, header, [orphan])
            refresh_unified_manifest(root)

            with self.assertRaisesRegex(SQLiteBuildError, "FOREIGN KEY"):
                SQLiteBuildPipeline(root).build()
            self.assertFalse(
                (root / "data/derived/sqlite" / DATABASE_FILENAME).exists()
            )

    def test_row_loss_during_load_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            pipeline = SQLiteBuildPipeline(root)
            original = pipeline._iter_typed_rows

            def dropping_first_master(item):
                for index, row in enumerate(original(item)):
                    if item.table == "master" and index == 0:
                        continue
                    yield row

            pipeline._iter_typed_rows = dropping_first_master
            with self.assertRaisesRegex(SQLiteBuildError, "Row preservation failed"):
                pipeline.build()
            self.assertFalse(pipeline.database_path.exists())

    def test_corrupted_input_preserves_existing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            output = root / "data/derived/sqlite"
            output.mkdir(parents=True)
            existing = {
                DATABASE_FILENAME: b"existing-database",
                "build_manifest.json": b"existing-manifest\n",
                "build_summary.md": b"existing-summary\n",
            }
            for name, value in existing.items():
                (output / name).write_bytes(value)
            with (root / "data/canonical/unified/master.csv").open("ab") as handle:
                handle.write(b"corruption")

            with self.assertRaisesRegex(SQLiteBuildError, "mismatch"):
                SQLiteBuildPipeline(root).build()
            for name, value in existing.items():
                self.assertEqual((output / name).read_bytes(), value)

    def test_portable_no_fts_profile_still_builds_base_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            pipeline = SQLiteBuildPipeline(root)
            pipeline._probe_capabilities = lambda: SQLiteCapabilities(
                sqlite_version=sqlite3.sqlite_version,
                strict=True,
                fts5=False,
                trigram=False,
                unicode61=False,
                profile="none",
            )

            result = pipeline.build()
            self.assertEqual(result.capabilities.profile, "none")
            self.assertEqual(result.validation["fts"]["status"], "not_applicable")
            with closing(sqlite3.connect(result.database_path)) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM sqlite_schema WHERE name='admissions_fts'"
                ).fetchone()[0]
                metadata = connection.execute(
                    "SELECT fts5_enabled, fts_tokenizer FROM build_metadata"
                ).fetchone()
            self.assertEqual(count, 0)
            self.assertEqual(metadata, (0, "none"))

    def test_unknown_substring_like_academic_field_is_unmapped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root, academic_field="理学療法X")
            result = SQLiteBuildPipeline(root).build()
            with closing(sqlite3.connect(result.database_path)) as connection:
                statuses = connection.execute(
                    """
                    SELECT mapping_status, COUNT(*)
                    FROM admission_search_academic_fields GROUP BY mapping_status
                    """
                ).fetchall()
                child_rows = connection.execute(
                    "SELECT COUNT(*) FROM admission_search_academic_field_groups"
                ).fetchone()[0]
            self.assertEqual(statuses, [("unmapped", 2)])
            self.assertEqual(child_rows, 0)

    def test_future_grade_expression_is_unmapped_without_numeric_floor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(
                root, gpa_requirement="将来追加された未監査表現4.0以上"
            )
            result = SQLiteBuildPipeline(root).build()
            with closing(sqlite3.connect(result.database_path)) as connection:
                rows = connection.execute(
                    """
                    SELECT grade_requirement_status, overall_gpa_min_tenths,
                           parse_status
                    FROM admission_search_grade_requirements
                    ORDER BY admission_rowid
                    """
                ).fetchall()
            self.assertEqual(rows, [("unmapped", None, "unmapped")] * 2)

    def test_single_and_review_required_child_cardinality(self) -> None:
        cases = (
            ("理学療法", "single", 2),
            ("国際", "review_required", 0),
        )
        for raw_value, expected_status, expected_children in cases:
            with self.subTest(raw_value=raw_value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prepare_unified_fixture(root, academic_field=raw_value)
                result = SQLiteBuildPipeline(root).build()
                with closing(sqlite3.connect(result.database_path)) as connection:
                    statuses = connection.execute(
                        """
                        SELECT DISTINCT mapping_status
                        FROM admission_search_academic_fields
                        """
                    ).fetchall()
                    child_rows = connection.execute(
                        "SELECT COUNT(*) FROM admission_search_academic_field_groups"
                    ).fetchone()[0]
                self.assertEqual(statuses, [(expected_status,)])
                self.assertEqual(child_rows, expected_children)

    def test_null_academic_field_is_not_applicable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root, academic_field=None)
            result = SQLiteBuildPipeline(root).build()
            with closing(sqlite3.connect(result.database_path)) as connection:
                rows = connection.execute(
                    """
                    SELECT raw_value, mapping_status
                    FROM admission_search_academic_fields
                    ORDER BY admission_rowid
                    """
                ).fetchall()
                child_rows = connection.execute(
                    "SELECT COUNT(*) FROM admission_search_academic_field_groups"
                ).fetchone()[0]
            self.assertEqual(rows, [(None, "not_applicable"), (None, "not_applicable")])
            self.assertEqual(child_rows, 0)

    def test_invalid_group_is_rejected_by_database_foreign_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            result = SQLiteBuildPipeline(root).build()
            with closing(sqlite3.connect(result.database_path)) as connection:
                connection.execute("PRAGMA foreign_keys=ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """
                        INSERT INTO admission_search_academic_field_groups
                            (admission_rowid, group_code, group_order, mapping_basis)
                        VALUES (1, 'invalid_group', 99, 'exact_crosswalk')
                        """
                    )

    def test_crosswalk_sha_mismatch_fails_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            crosswalk = (
                root
                / "schema/academic_field/academic_field_crosswalk_v0_2.csv"
            )
            crosswalk.write_text(
                crosswalk.read_text(encoding="utf-8").replace(
                    "Reviewed exact raw-value mapping.",
                    "Reviewed exact raw-value mapping!",
                    1,
                ),
                encoding="utf-8",
                newline="",
            )
            pipeline = SQLiteBuildPipeline(root)
            with self.assertRaisesRegex(
                SQLiteBuildError, "crosswalk SHA-256 differs"
            ):
                pipeline.build()
            self.assertFalse(pipeline.database_path.exists())

    def test_academic_field_layer_rebuild_is_logically_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_unified_fixture(root)
            first = SQLiteBuildPipeline(root, output_dir="derived-one").build()
            second = SQLiteBuildPipeline(root, output_dir="derived-two").build()

            def rows(path: Path, table: str) -> list[tuple[object, ...]]:
                with closing(sqlite3.connect(path)) as connection:
                    return connection.execute(
                        f"SELECT * FROM {table} ORDER BY 1, 2"
                    ).fetchall()

            for table in (
                "academic_field_taxonomy",
                "admission_search_academic_fields",
                "admission_search_academic_field_groups",
            ):
                self.assertEqual(
                    rows(first.database_path, table),
                    rows(second.database_path, table),
                )
            first_manifest = json.loads(
                first.manifest_path.read_text(encoding="utf-8")
            )
            second_manifest = json.loads(
                second.manifest_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                first_manifest["academic_field_search"],
                second_manifest["academic_field_search"],
            )
            self.assertEqual(
                first_manifest["inputs"]["academic_field_crosswalk"]["sha256"],
                second_manifest["inputs"]["academic_field_crosswalk"]["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
