from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from early_admissions.site_data_builder import SiteDataBuildError, SiteDataBuildPipeline
from early_admissions.site_search import SiteSearchError, load_search_rows
from early_admissions.sqlite_builder import SQLiteBuildPipeline

from tests.test_sqlite_build import prepare_unified_fixture
from tests.test_validator import REPO_ROOT


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_site_fixture(root: Path, *, duplicate_children: bool = False) -> Path:
    prepare_unified_fixture(root, duplicate_children=duplicate_children, gpa_requirement="3.5以上")
    destination = root / "schema/site"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO_ROOT / "schema/site", destination)
    return SQLiteBuildPipeline(root).build().database_path


def load_all_details(output: Path) -> list[dict[str, object]]:
    manifest = json.loads((output / "build_manifest.json").read_text(encoding="utf-8"))
    details: list[dict[str, object]] = []
    for item in manifest["outputs"]["artifacts"]:
        if item["kind"] == "detail_shard":
            payload = json.loads((output / item["path"]).read_text(encoding="utf-8"))
            details.extend(payload["details"])
    return details


class SiteDataBuildTests(unittest.TestCase):
    def test_successful_build_preserves_rows_raw_nulls_and_booleans(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = prepare_site_fixture(root)
            before = sha256(database)
            result = SiteDataBuildPipeline(root, build_timestamp_utc="2026-09-20T00:00:00Z").build()
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            rows = load_search_rows(result.output_dir)
            details = load_all_details(result.output_dir)
            self.assertEqual((len(rows), len(details)), (2, 2))
            self.assertEqual(len({(r["source_dataset"], r["source_version"], r["record_id"]) for r in rows}), 2)
            kokkoritsu = next(r for r in rows if r["source_dataset"] == "kokkoritsu")
            self.assertIsNone(kokkoritsu["prefecture"])
            self.assertIs(kokkoritsu["stem_flag"], True)
            self.assertIs(kokkoritsu["fallback_previous_year"], False)
            self.assertEqual(kokkoritsu["academic_field_groups"], ["natural_sciences", "engineering", "information"])
            self.assertEqual(
                kokkoritsu["academic_field_v2_broad_mapping_status"], "multi"
            )
            self.assertTrue(kokkoritsu["academic_field_v2_broad_memberships"])
            self.assertEqual(
                kokkoritsu["academic_field_v2_mapping_contract_version"], "0.2"
            )
            self.assertEqual(kokkoritsu["gpa_min_tenths"], 35)
            self.assertIn("selection_practical", kokkoritsu)
            self.assertIn("selection_group_discussion", kokkoritsu)
            self.assertIn("selection_aptitude_test", kokkoritsu)
            self.assertEqual(manifest["validation"]["search_equivalence"]["queries"], 25)
            self.assertEqual(
                manifest["grade_requirement_search"]["numeric_floor_rows"], 2
            )
            self.assertEqual(
                manifest["grade_requirement_search"]["raw_mismatch_rows"], 0
            )
            self.assertEqual(sha256(database), before)
            filter_receipt = next(
                item
                for item in manifest["outputs"]["artifacts"]
                if item["kind"] == "filter_options"
            )
            filter_options = json.loads(
                (result.output_dir / filter_receipt["path"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                len(filter_options["academic_field_v2_broad_groups"]), 30
            )
            self.assertEqual(
                len(filter_options["academic_field_v2_subcategories"]), 89
            )

    def test_exact_duplicate_children_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_site_fixture(root, duplicate_children=True)
            result = SiteDataBuildPipeline(root).build()
            details = load_all_details(result.output_dir)
            children = [child for detail in details for child in detail["research_requirements"]]
            self.assertEqual(len(children), 2)
            first, second = children
            self.assertNotEqual(first["research_rowid"], second["research_rowid"])
            self.assertEqual({k: v for k, v in first.items() if k != "research_rowid"}, {k: v for k, v in second.items() if k != "research_rowid"})

    def test_manifest_input_sha_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_site_fixture(root)
            path = root / "data/derived/sqlite/build_manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["output"]["sha256"] = "0" * 64
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(SiteDataBuildError, "SHA-256"):
                SiteDataBuildPipeline(root).build()

    def test_schema_version_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_site_fixture(root)
            path = root / "data/derived/sqlite/build_manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["database_schema_version"] = "9.9"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(SiteDataBuildError, "schema version"):
                SiteDataBuildPipeline(root).build()

    def test_deterministic_build_excluding_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_site_fixture(root)
            first = SiteDataBuildPipeline(
                root, output_dir=Path("data/derived/site/a"), qa_report_path=Path("qa-a.md"), build_timestamp_utc="2026-09-20T00:00:00Z"
            ).build()
            second = SiteDataBuildPipeline(
                root, output_dir=Path("data/derived/site/b"), qa_report_path=Path("qa-b.md"), build_timestamp_utc="2026-09-21T00:00:00Z"
            ).build()
            files_a = {p.relative_to(first.output_dir): p.read_bytes() for p in first.output_dir.rglob("*") if p.is_file()}
            files_b = {p.relative_to(second.output_dir): p.read_bytes() for p in second.output_dir.rglob("*") if p.is_file()}
            manifest_a = json.loads(files_a.pop(Path("build_manifest.json")))
            manifest_b = json.loads(files_b.pop(Path("build_manifest.json")))
            manifest_a.pop("build_timestamp_utc")
            manifest_b.pop("build_timestamp_utc")
            self.assertEqual(files_a, files_b)
            self.assertEqual(manifest_a, manifest_b)

    def test_missing_detail_and_corrupt_search_shard_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_site_fixture(root)
            result = SiteDataBuildPipeline(root).build()
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            detail = next(item for item in manifest["outputs"]["artifacts"] if item["kind"] == "detail_shard")
            (result.output_dir / detail["path"]).unlink()
            with self.assertRaisesRegex(SiteSearchError, "missing or corrupt"):
                load_search_rows(result.output_dir)

            result = SiteDataBuildPipeline(root).build()
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            search = next(item for item in manifest["outputs"]["artifacts"] if item["kind"] == "search_shard")
            with (result.output_dir / search["path"]).open("ab") as handle:
                handle.write(b"corrupt")
            with self.assertRaisesRegex(SiteSearchError, "missing or corrupt"):
                load_search_rows(result.output_dir)

    def test_failed_build_does_not_replace_existing_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_site_fixture(root)
            result = SiteDataBuildPipeline(root).build()
            before = sha256(result.manifest_path)
            sqlite_manifest = root / "data/derived/sqlite/build_manifest.json"
            data = json.loads(sqlite_manifest.read_text(encoding="utf-8"))
            data["output"]["sha256"] = "f" * 64
            sqlite_manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(SiteDataBuildError):
                SiteDataBuildPipeline(root).build()
            self.assertEqual(sha256(result.manifest_path), before)


class CurrentSiteDataRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        temporary = Path(cls.temporary.name)
        cls.result = SiteDataBuildPipeline(
            REPO_ROOT,
            output_dir=temporary / "site",
            qa_report_path=temporary / "qa.md",
            build_timestamp_utc="2026-09-20T00:00:00Z",
        ).build()
        cls.manifest = json.loads(
            cls.result.manifest_path.read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_current_snapshot_counts_and_regressions(self) -> None:
        self.assertEqual(self.manifest["counts"]["search_rows"], 5921)
        self.assertEqual(self.manifest["counts"]["detail_records"], 5921)
        self.assertEqual(self.manifest["counts"]["research_requirement_rows"], 437)
        self.assertEqual(
            self.manifest["validation"]["search_equivalence"]["gpa_safe_match_counts"],
            {"3.0": 72, "3.5": 490, "3.8": 743, "4.0": 1124, "4.5": 1199},
        )
        self.assertEqual(
            self.manifest["counts"]["academic_field_mapping_statuses"],
            {"single": 4069, "multi": 1833, "review_required": 19},
        )
        self.assertEqual(
            sum(self.manifest["counts"]["academic_field_group_memberships"].values()),
            7952,
        )
        self.assertEqual(
            self.manifest["validation"]["search_equivalence"]["queries"], 25
        )
        self.assertEqual(
            self.manifest["grade_requirement_search"]["classification_counts"],
            {
                "required": 2286,
                "not_required": 339,
                "review_required": 1291,
                "unknown": 1985,
                "not_applicable": 20,
                "unmapped": 0,
            },
        )
        self.assertEqual(
            self.manifest["grade_requirement_search"]["numeric_floor_rows"],
            1329,
        )
        self.assertEqual(
            self.manifest["counts"]["academic_field_v2_broad_membership_rows"],
            8275,
        )
        self.assertEqual(
            self.manifest["counts"][
                "academic_field_v2_subcategory_membership_rows"
            ],
            6880,
        )
        self.assertEqual(
            self.manifest["validation"]["search_equivalence"][
                "academic_field_v2"
            ]["branch_query"]["rows"],
            1796,
        )
        self.assertEqual(
            self.manifest["validation"]["search_equivalence"][
                "academic_field_v2"
            ]["branch_frozen_logical_keys"],
            "passed",
        )


if __name__ == "__main__":
    unittest.main()
