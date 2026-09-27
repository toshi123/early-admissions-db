from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from early_admissions.unified_adapter import (
    CanonicalSourceLoader,
    UnifiedAdapter,
)
from early_admissions.unified_builder import (
    UnifiedBuildError,
    UnifiedBuildPipeline,
)

from tests.test_validator import REPO_ROOT, build_synthetic_repo, write_csv


WORKING_V0_3_ROWS = {
    "master": 6_585,
    "coverage": 260,
    "research_requirements": 495,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path)
        for path in sorted((root / "data" / "canonical").glob("*/*.csv"))
        if path.parent.name in {"kokkoritsu", "shidai"}
    }


class UnifiedAdapterTests(unittest.TestCase):
    def test_loss_aware_mapping_preserves_raw_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            states = build_synthetic_repo(root)
            state = states["kokkoritsu"]
            master = dict(state["master"])
            master.update(
                {
                    "common_test_required": "条件付き",
                    "research_activity_level": "activity_based",
                    "detail_completeness": "説明文",
                    "application_start": " 2026-11-01（予定） ",
                    "notes": " 余白を保持 ",
                }
            )
            write_csv(
                state["canonical"] / "master.csv",
                state["master_header"],
                [master],
            )

            bundle = CanonicalSourceLoader(root).load()
            contract = json.loads(
                (root / "schema/unified/early_admissions_unified_schema_v0_3.json")
                .read_text(encoding="utf-8")
            )
            adapter = UnifiedAdapter(contract)
            record = adapter.adapt_master(master, "kokkoritsu", "5.83")

            self.assertEqual(record["common_test_required"], "Conditional")
            self.assertEqual(record["research_activity_level_status"], "unmapped")
            self.assertEqual(record["research_activity_level_raw"], "activity_based")
            self.assertEqual(record["detail_completeness_status"], "unmapped")
            self.assertEqual(record["detail_completeness_raw"], "説明文")
            self.assertEqual(record["application_start"], " 2026-11-01（予定） ")
            self.assertEqual(record["notes"], " 余白を保持 ")
            self.assertEqual(
                list(record),
                list(contract["x-table-contracts"]["master"]["csv_columns"]),
            )
            self.assertEqual(len(bundle.table("kokkoritsu", "master").rows), 1)


class UnifiedBuildPipelineTests(unittest.TestCase):
    def _add_duplicate_research_rows(
        self, states: dict[str, dict[str, object]]
    ) -> None:
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

    def test_build_validates_preserves_duplicates_and_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            states = build_synthetic_repo(root)
            self._add_duplicate_research_rows(states)
            before = canonical_hashes(root)
            expected = {
                "master": 2,
                "coverage": 2,
                "research_requirements": 2,
            }

            result = UnifiedBuildPipeline(root).build()
            first_hashes = {
                table: sha256(result.output_dir / f"{table}.csv")
                for table in expected
            }
            first_manifest = result.manifest_path.read_bytes()
            second = UnifiedBuildPipeline(root).build()
            second_hashes = {
                table: sha256(second.output_dir / f"{table}.csv")
                for table in expected
            }

            self.assertEqual(first_hashes, second_hashes)
            self.assertEqual(first_manifest, second.manifest_path.read_bytes())
            self.assertEqual(before, canonical_hashes(root))

            contract = json.loads(
                (root / "schema/unified/early_admissions_unified_schema_v0_3.json")
                .read_text(encoding="utf-8")
            )
            for table, row_count in expected.items():
                path = result.output_dir / f"{table}.csv"
                raw = path.read_bytes()
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                with path.open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.reader(handle)
                    header = next(reader)
                    rows = list(reader)
                self.assertEqual(
                    header,
                    contract["x-table-contracts"][table]["csv_columns"],
                )
                self.assertEqual(len(rows), row_count)

            with (
                result.output_dir / "research_requirements.csv"
            ).open("r", encoding="utf-8", newline="") as handle:
                research_rows = list(csv.DictReader(handle))
            self.assertEqual(research_rows[0], research_rows[1])

            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["contract_version"], "0.3")
            self.assertEqual(
                manifest["source_versions"],
                {"kokkoritsu": "5.83", "shidai": "1.10"},
            )
            self.assertTrue(
                manifest["validation"]["determinism"]["byte_identical"]
            )
            self.assertEqual(
                manifest["validation"]["unified"]
                ["research_duplicate_preservation"]
                ["source_exact_duplicate_excess_rows"],
                1,
            )
            self.assertEqual(
                manifest["validation"]["unified"]
                ["research_duplicate_preservation"]
                ["output_exact_duplicate_excess_rows"],
                1,
            )
            self.assertEqual(
                manifest["validation"]["unified"]["row_preservation"]
                ["output_rows"],
                expected,
            )

    def test_added_source_row_increases_dynamic_expected_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            states = build_synthetic_repo(root)
            state = states["kokkoritsu"]
            first_master = dict(state["master"])
            second_master = dict(first_master)
            second_master["record_id"] = "KOKKORITSU-2"
            write_csv(
                state["canonical"] / "master.csv",
                state["master_header"],
                [first_master, second_master],
            )
            coverage = dict(state["coverage"])
            coverage["master_rows"] = "2"
            write_csv(
                state["canonical"] / "coverage.csv",
                state["coverage_header"],
                [coverage],
            )

            result = UnifiedBuildPipeline(root).build()
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            preservation = manifest["validation"]["unified"]["row_preservation"]
            expected = {
                "master": 3,
                "coverage": 2,
                "research_requirements": 0,
            }
            self.assertEqual(preservation["expectation_source"], "canonical_input")
            self.assertEqual(preservation["expected_output_rows"], expected)
            self.assertEqual(preservation["input_rows"], expected)
            self.assertEqual(preservation["output_rows"], expected)

    def test_dropped_adapter_row_fails_row_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_synthetic_repo(root)
            output_dir = root / "data/canonical/unified"
            output_dir.mkdir(parents=True)
            existing = output_dir / "master.csv"
            existing.write_bytes(b"existing-output\n")

            pipeline = UnifiedBuildPipeline(root)
            original_iter_records = pipeline.adapter.iter_records

            def dropping_iter_records(bundle, table):
                for index, record in enumerate(original_iter_records(bundle, table)):
                    if table == "master" and index == 0:
                        continue
                    yield record

            pipeline.adapter.iter_records = dropping_iter_records
            with self.assertRaisesRegex(UnifiedBuildError, "Row preservation failed"):
                pipeline.build()

            self.assertEqual(existing.read_bytes(), b"existing-output\n")
            self.assertFalse((output_dir / "coverage.csv").exists())
            self.assertFalse((output_dir / "build_manifest.json").exists())

    def test_external_output_directory_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as source_directory:
            root = Path(source_directory)
            build_synthetic_repo(root)
            with tempfile.TemporaryDirectory() as output_directory:
                output_dir = Path(output_directory) / "unified"
                result = UnifiedBuildPipeline(root, output_dir=output_dir).build()
                manifest = json.loads(
                    result.manifest_path.read_text(encoding="utf-8")
                )

            self.assertEqual(
                manifest["outputs"]["master"]["path"],
                str(output_dir / "master.csv"),
            )


class WorkingV03RegressionTests(unittest.TestCase):
    def test_v5_83_v1_10_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = UnifiedBuildPipeline(
                REPO_ROOT,
                output_dir=Path(directory) / "unified",
            ).build()
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            preservation = manifest["validation"]["unified"]["row_preservation"]
            actual_rows = {
                table: metadata["rows"]
                for table, metadata in result.output_metadata.items()
            }

        self.assertEqual(preservation["expectation_source"], "canonical_input")
        self.assertEqual(preservation["expected_output_rows"], WORKING_V0_3_ROWS)
        self.assertEqual(actual_rows, WORKING_V0_3_ROWS)


if __name__ == "__main__":
    unittest.main()
