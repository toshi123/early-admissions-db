"""Deterministic build pipeline for unified early-admissions data v0.1."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .unified_adapter import (
    SOURCE_ORDER,
    TABLE_ORDER,
    CanonicalBundle,
    CanonicalSourceLoader,
    UnifiedAdapter,
    null_if_blank,
    write_unified_table,
)
from .validator import CONTRACT_DOCUMENTS, CONTRACT_PATH, ReadOnlyValidator, parse_int


DEFAULT_OUTPUT_DIR = Path("data/canonical/unified")
OUTPUT_FILENAMES = {
    "master": "master.csv",
    "coverage": "coverage.csv",
    "research_requirements": "research_requirements.csv",
}
RECORD_DEFS = {
    "master": "masterRecord",
    "coverage": "coverageRecord",
    "research_requirements": "researchRequirementRecord",
}
INTEGER_FIELDS = {
    "master": {"admission_year", "information_year"},
    "coverage": {"master_rows"},
    "research_requirements": set(),
}
BOOLEAN_FIELDS = {
    "master": {"stem_flag", "fallback_previous_year"},
    "coverage": set(),
    "research_requirements": set(),
}


class UnifiedBuildError(RuntimeError):
    """Raised when a build gate fails before publication."""


@dataclass(frozen=True)
class UnifiedBuildResult:
    """Published artifact locations and their deterministic metadata."""

    output_dir: Path
    manifest_path: Path
    summary_path: Path
    output_metadata: Mapping[str, Mapping[str, Any]]
    source_validation_summary: Mapping[str, Any]


class UnifiedBuildPipeline:
    """Build, validate, reproduce, and publish unified v0.1 CSV artifacts."""

    def __init__(
        self,
        repo_root: Path | str,
        *,
        output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        output_path = Path(output_dir)
        self.output_dir = (
            output_path if output_path.is_absolute() else self.repo_root / output_path
        )
        self.schema_path = self.repo_root / CONTRACT_PATH
        self.contract = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.contract_version = str(
            self.contract["properties"]["contract_version"]["const"]
        )
        self.adapter = UnifiedAdapter(self.contract)

    def build(self) -> UnifiedBuildResult:
        """Execute every validation gate, then publish only complete artifacts."""

        source_result = ReadOnlyValidator(self.repo_root).validate()
        source_summary = source_result.summary()
        if source_summary["by_severity"]["error"]:
            raise UnifiedBuildError(
                "Source canonical validation failed with "
                f"{source_summary['by_severity']['error']} error(s); nothing published."
            )

        bundle = CanonicalSourceLoader(self.repo_root).load()
        self._validate_version_matrix(bundle)

        self.output_dir.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".unified-build-", dir=self.output_dir.parent
        ) as temporary:
            work_root = Path(temporary)
            first_dir = work_root / "first"
            second_dir = work_root / "second"
            first_metadata = self._write_build(first_dir, bundle)
            second_metadata = self._write_build(second_dir, bundle)

            deterministic = self._assert_byte_identical(first_dir, second_dir)
            validation = self._validate_generated(first_dir, bundle)
            self._assert_sources_unchanged(bundle)

            publish_dir = work_root / "publish"
            publish_dir.mkdir()
            for table in TABLE_ORDER:
                shutil.copyfile(
                    first_dir / OUTPUT_FILENAMES[table],
                    publish_dir / OUTPUT_FILENAMES[table],
                )

            manifest = self._build_manifest(
                bundle=bundle,
                output_metadata=first_metadata,
                source_summary=source_summary,
                generated_validation=validation,
                deterministic=deterministic,
            )
            manifest_path = publish_dir / "build_manifest.json"
            summary_path = publish_dir / "build_summary.md"
            write_text_lf(
                manifest_path,
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
            )
            write_text_lf(summary_path, self._build_summary(manifest))
            self._publish(publish_dir)

        return UnifiedBuildResult(
            output_dir=self.output_dir,
            manifest_path=self.output_dir / "build_manifest.json",
            summary_path=self.output_dir / "build_summary.md",
            output_metadata=first_metadata,
            source_validation_summary=source_summary,
        )

    def _write_build(
        self, destination: Path, bundle: CanonicalBundle
    ) -> dict[str, dict[str, Any]]:
        destination.mkdir(parents=True, exist_ok=True)
        metadata: dict[str, dict[str, Any]] = {}
        for table in TABLE_ORDER:
            item = write_unified_table(
                destination / OUTPUT_FILENAMES[table],
                self.adapter.columns[table],
                self.adapter.iter_records(bundle, table),
            )
            item["path"] = portable_manifest_path(
                self.output_dir / OUTPUT_FILENAMES[table], self.repo_root
            )
            metadata[table] = item
        return metadata

    def _assert_byte_identical(
        self, first_dir: Path, second_dir: Path
    ) -> dict[str, Any]:
        hashes: dict[str, str] = {}
        for table in TABLE_ORDER:
            filename = OUTPUT_FILENAMES[table]
            first = (first_dir / filename).read_bytes()
            second = (second_dir / filename).read_bytes()
            if first != second:
                raise UnifiedBuildError(
                    f"Determinism check failed for {filename}; nothing published."
                )
            hashes[table] = hashlib.sha256(first).hexdigest()
        return {
            "status": "passed",
            "builds_compared": 2,
            "byte_identical": True,
            "sha256": hashes,
        }

    def _validate_generated(
        self, directory: Path, bundle: CanonicalBundle
    ) -> dict[str, Any]:
        records: dict[str, list[dict[str, Any]]] = {}
        schema_counts: dict[str, int] = {}
        for table in TABLE_ORDER:
            table_records = self._read_generated_table(
                directory / OUTPUT_FILENAMES[table], table
            )
            self._validate_records_against_schema(table, table_records)
            records[table] = table_records
            schema_counts[table] = len(table_records)

        input_counts = {
            table: sum(
                len(bundle.table(dataset, table).rows) for dataset in SOURCE_ORDER
            )
            for table in TABLE_ORDER
        }
        output_counts = {table: len(records[table]) for table in TABLE_ORDER}
        if output_counts != input_counts:
            raise UnifiedBuildError(
                f"Row preservation failed: inputs={input_counts}, outputs={output_counts}"
            )

        self._validate_exact_adapter_projection(records, bundle)
        self._validate_lossless_source_values(records, bundle)
        relational = self._validate_relations(records)
        source_counts = self._validate_provenance(records, bundle)
        duplicate_counts = self._validate_duplicate_preservation(records, bundle)
        return {
            "json_schema": {
                "status": "passed",
                "validated_rows": schema_counts,
            },
            "relational": relational,
            "row_preservation": {
                "status": "passed",
                "expectation_source": "canonical_input",
                "expected_output_rows": input_counts,
                "input_rows": input_counts,
                "output_rows": output_counts,
            },
            "source_provenance": {
                "status": "passed",
                "rows_by_table_and_dataset": source_counts,
            },
            "raw_source_values": {
                "status": "passed",
                "policy": "copy/raw fields and status raw companions preserved exactly",
            },
            "research_duplicate_preservation": {
                "status": "passed",
                **duplicate_counts,
            },
            "serialization": {
                "status": "passed",
                "encoding": "UTF-8",
                "line_endings": "LF",
                "bom": False,
                "column_order": "unified_schema",
            },
        }

    def _read_generated_table(
        self, path: Path, table: str
    ) -> list[dict[str, Any]]:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise UnifiedBuildError(f"Generated CSV contains a BOM: {path.name}")
        if b"\r" in raw:
            raise UnifiedBuildError(f"Generated CSV is not LF-only: {path.name}")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise UnifiedBuildError(
                f"Generated CSV is not valid UTF-8: {path.name}"
            ) from error

        expected_header = list(self.adapter.columns[table])
        output: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != expected_header:
                raise UnifiedBuildError(
                    f"Generated column order mismatch in {path.name}"
                )
            for row_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise UnifiedBuildError(
                        f"Generated row width mismatch at {path.name}:{row_number}"
                    )
                output.append(
                    {
                        field: self._deserialize_value(
                            table, field, value, path.name, row_number
                        )
                        for field, value in row.items()
                    }
                )
        return output

    @staticmethod
    def _deserialize_value(
        table: str, field: str, value: str, filename: str, row_number: int
    ) -> Any:
        if value == "":
            return None
        if field in INTEGER_FIELDS[table]:
            parsed = parse_int(value)
            if parsed is None or str(parsed) != value:
                raise UnifiedBuildError(
                    f"Non-canonical integer at {filename}:{row_number}:{field}"
                )
            return parsed
        if field in BOOLEAN_FIELDS[table]:
            if value not in {"true", "false"}:
                raise UnifiedBuildError(
                    f"Invalid boolean at {filename}:{row_number}:{field}"
                )
            return value == "true"
        return value

    def _validate_records_against_schema(
        self, table: str, records: Sequence[Mapping[str, Any]]
    ) -> None:
        record_schema = {
            "$schema": self.contract["$schema"],
            "$defs": self.contract["$defs"],
            "$ref": f"#/$defs/{RECORD_DEFS[table]}",
        }
        Draft202012Validator.check_schema(record_schema)
        validator = Draft202012Validator(record_schema)
        for row_number, record in enumerate(records, start=2):
            error = next(iter(validator.iter_errors(record)), None)
            if error is not None:
                field_path = ".".join(str(part) for part in error.path) or "<row>"
                raise UnifiedBuildError(
                    f"JSON Schema validation failed at {table}.csv:{row_number}:"
                    f"{field_path}: {error.message}"
                )

    def _validate_exact_adapter_projection(
        self,
        records: Mapping[str, Sequence[Mapping[str, Any]]],
        bundle: CanonicalBundle,
    ) -> None:
        for table in TABLE_ORDER:
            expected = list(self.adapter.iter_records(bundle, table))
            actual = list(records[table])
            if actual != expected:
                for index, (left, right) in enumerate(zip(actual, expected), start=2):
                    if left != right:
                        differing = [
                            key for key in left if left.get(key) != right.get(key)
                        ]
                        raise UnifiedBuildError(
                            f"Source projection mismatch at {table}.csv:{index}; "
                            f"fields={differing[:5]}"
                        )
                raise UnifiedBuildError(
                    f"Source projection length mismatch for {table}.csv"
                )

    @staticmethod
    def _validate_lossless_source_values(
        records: Mapping[str, Sequence[Mapping[str, Any]]],
        bundle: CanonicalBundle,
    ) -> None:
        """Independently assert that every raw/copy source value is unchanged."""

        normalized_master_fields = {
            "admission_year",
            "information_year",
            "stem_flag",
            "fallback_previous_year",
            "common_test_required",
            "research_activity_level",
            "detail_completeness",
        }
        output_index = {table: 0 for table in TABLE_ORDER}
        for table in TABLE_ORDER:
            for dataset in SOURCE_ORDER:
                source_table = bundle.table(dataset, table)
                for source_row in source_table.rows:
                    index = output_index[table]
                    output_row = records[table][index]
                    output_index[table] += 1
                    if output_row["source_dataset"] != dataset:
                        raise UnifiedBuildError(
                            f"source_dataset changed at {table}.csv:{index + 2}"
                        )
                    if output_row["source_version"] != source_table.source_version:
                        raise UnifiedBuildError(
                            f"source_version changed at {table}.csv:{index + 2}"
                        )

                    for field, raw in source_row.items():
                        if table == "master" and field in normalized_master_fields:
                            continue
                        if table == "coverage" and field == "master_rows":
                            continue
                        if output_row[field] != null_if_blank(raw):
                            raise UnifiedBuildError(
                                f"Raw source value changed at {table}.csv:"
                                f"{index + 2}:{field}"
                            )

                    if table == "master":
                        if output_row["research_activity_level_raw"] != null_if_blank(
                            source_row["research_activity_level"]
                        ):
                            raise UnifiedBuildError(
                                "research_activity_level_raw does not preserve source "
                                f"at master.csv:{index + 2}"
                            )
                        if output_row["detail_completeness_raw"] != null_if_blank(
                            source_row["detail_completeness"]
                        ):
                            raise UnifiedBuildError(
                                "detail_completeness_raw does not preserve source at "
                                f"master.csv:{index + 2}"
                            )

    def _validate_relations(
        self, records: Mapping[str, Sequence[Mapping[str, Any]]]
    ) -> dict[str, Any]:
        master_keys: set[tuple[Any, ...]] = set()
        master_group_counts: Counter[tuple[Any, ...]] = Counter()
        for record in records["master"]:
            key = (
                record["source_dataset"],
                record["source_version"],
                record["record_id"],
            )
            if None in key or key in master_keys:
                raise UnifiedBuildError(f"Invalid or duplicate unified Master key: {key}")
            master_keys.add(key)
            master_group_counts[
                (
                    record["source_dataset"],
                    record["source_version"],
                    record["institution_type"],
                    record["university"],
                )
            ] += 1

        coverage_keys: set[tuple[Any, ...]] = set()
        for record in records["coverage"]:
            key = (
                record["source_dataset"],
                record["source_version"],
                record["institution_type"],
                record["university"],
            )
            if None in key or key in coverage_keys:
                raise UnifiedBuildError(f"Invalid or duplicate unified Coverage key: {key}")
            coverage_keys.add(key)
            actual = master_group_counts[key]
            if record["master_rows"] != actual:
                raise UnifiedBuildError(
                    f"Unified Coverage.master_rows mismatch for {key}: "
                    f"declared={record['master_rows']}, actual={actual}"
                )

        for record in records["research_requirements"]:
            key = (
                record["source_dataset"],
                record["source_version"],
                record["admission_id"],
            )
            if None in key or key not in master_keys:
                raise UnifiedBuildError(f"Unified ResearchRequirements orphan FK: {key}")

        return {
            "status": "passed",
            "master_primary_key": "passed",
            "coverage_key": "passed",
            "coverage_master_rows": "passed",
            "research_requirements_foreign_key": "passed",
        }

    def _validate_provenance(
        self,
        records: Mapping[str, Sequence[Mapping[str, Any]]],
        bundle: CanonicalBundle,
    ) -> dict[str, dict[str, int]]:
        expected_matrix = self.contract["x-source-version-matrix"]
        output: dict[str, dict[str, int]] = {}
        for table in TABLE_ORDER:
            counts: Counter[str] = Counter()
            for record in records[table]:
                dataset = record["source_dataset"]
                version = record["source_version"]
                if expected_matrix.get(dataset) != version:
                    raise UnifiedBuildError(
                        f"Invalid source provenance pair in {table}: "
                        f"{dataset}/{version}"
                    )
                if table != "research_requirements":
                    if dataset == "kokkoritsu" and record[
                        "institution_type"
                    ] not in {"国立", "公立"}:
                        raise UnifiedBuildError(
                            f"Institution type conflicts with source dataset in {table}"
                        )
                    if dataset == "shidai" and record["institution_type"] != "私立":
                        raise UnifiedBuildError(
                            f"Institution type conflicts with source dataset in {table}"
                        )
                counts[dataset] += 1

            expected_counts = {
                dataset: len(bundle.table(dataset, table).rows)
                for dataset in SOURCE_ORDER
            }
            actual_counts = {dataset: counts[dataset] for dataset in SOURCE_ORDER}
            if actual_counts != expected_counts:
                raise UnifiedBuildError(
                    f"Source provenance row counts differ for {table}: "
                    f"expected={expected_counts}, actual={actual_counts}"
                )
            output[table] = actual_counts
        return output

    @staticmethod
    def _validate_duplicate_preservation(
        records: Mapping[str, Sequence[Mapping[str, Any]]],
        bundle: CanonicalBundle,
    ) -> dict[str, Any]:
        source_excess = 0
        for dataset in SOURCE_ORDER:
            rows = bundle.table(dataset, "research_requirements").rows
            counts = Counter(tuple(row.items()) for row in rows)
            source_excess += sum(count - 1 for count in counts.values() if count > 1)

        output_counts = Counter(
            tuple(record.items()) for record in records["research_requirements"]
        )
        output_excess = sum(
            count - 1 for count in output_counts.values() if count > 1
        )
        if output_excess != source_excess:
            raise UnifiedBuildError(
                "ResearchRequirements duplicate multiplicity changed: "
                f"source_excess={source_excess}, output_excess={output_excess}"
            )
        return {
            "source_exact_duplicate_excess_rows": source_excess,
            "output_exact_duplicate_excess_rows": output_excess,
        }

    def _validate_version_matrix(self, bundle: CanonicalBundle) -> None:
        expected = self.contract["x-source-version-matrix"]
        if dict(bundle.source_versions) != expected:
            raise UnifiedBuildError(
                f"Source version matrix mismatch: expected={expected}, "
                f"actual={dict(bundle.source_versions)}"
            )

    @staticmethod
    def _assert_sources_unchanged(bundle: CanonicalBundle) -> None:
        for dataset in SOURCE_ORDER:
            schema_meta = bundle.source_schema_metadata[dataset]
            schema_path = bundle.repo_root / schema_meta["path"]
            if sha256_file(schema_path) != schema_meta["sha256"]:
                raise UnifiedBuildError(
                    f"Source schema changed during build: {schema_meta['path']}"
                )
            for table in TABLE_ORDER:
                source = bundle.table(dataset, table)
                if sha256_file(source.path) != source.sha256:
                    raise UnifiedBuildError(
                        f"Canonical source changed during build: {source.path}"
                    )

    def _build_manifest(
        self,
        *,
        bundle: CanonicalBundle,
        output_metadata: Mapping[str, Mapping[str, Any]],
        source_summary: Mapping[str, Any],
        generated_validation: Mapping[str, Any],
        deterministic: Mapping[str, Any],
    ) -> dict[str, Any]:
        contract_inputs: dict[str, Any] = {}
        for rel_path in (*CONTRACT_DOCUMENTS, CONTRACT_PATH):
            path = self.repo_root / rel_path
            contract_inputs[str(rel_path)] = file_metadata(path, self.repo_root)

        source_schemas = {
            dataset: dict(bundle.source_schema_metadata[dataset])
            for dataset in SOURCE_ORDER
        }
        source_tables: dict[str, dict[str, Any]] = {}
        for dataset in SOURCE_ORDER:
            source_tables[dataset] = {}
            for table in TABLE_ORDER:
                item = bundle.table(dataset, table)
                source_tables[dataset][table] = {
                    "path": str(item.path.relative_to(self.repo_root)),
                    "rows": len(item.rows),
                    "columns": len(item.header),
                    "size_bytes": item.size_bytes,
                    "sha256": item.sha256,
                }

        compact_source_summary = {
            "status": source_summary["status"],
            "total_issues": source_summary["total_issues"],
            "by_severity": source_summary["by_severity"],
            "by_dataset": source_summary["by_dataset"],
            "by_code": source_summary["by_code"],
        }
        return {
            "manifest_version": "1",
            "artifact": "early_admissions_unified",
            "contract_version": self.contract_version,
            "schema_id": self.contract.get("$id"),
            "source_versions": dict(bundle.source_versions),
            "inputs": {
                "contract": contract_inputs,
                "source_schemas": source_schemas,
                "canonical_tables": source_tables,
            },
            "outputs": {table: dict(output_metadata[table]) for table in TABLE_ORDER},
            "validation": {
                "status": "passed",
                "source_canonical": compact_source_summary,
                "unified": dict(generated_validation),
                "determinism": dict(deterministic),
                "canonical_sources_unchanged_during_build": True,
            },
            "serialization": {
                "csv_encoding": "UTF-8",
                "csv_line_endings": "LF",
                "csv_bom": False,
                "null_csv": "empty cell",
                "row_order": "kokkoritsu source order, then shidai source order",
            },
            "excluded_artifacts": [
                "SQLite",
                "JSON search index",
                "Excel",
                "Site",
            ],
        }

    def _build_summary(self, manifest: Mapping[str, Any]) -> str:
        source = manifest["validation"]["source_canonical"]
        severity = source["by_severity"]
        lines = [
            "# Unified dataset v0.1 build summary",
            "",
            "- Build status: `passed`",
            f"- Contract/schema version: `{self.contract_version}`",
            "- Canonical source mode: read-only",
            "- Determinism: two builds were byte-identical",
            "- Serialization: UTF-8, LF, no BOM",
            "",
            "## Source versions",
            "",
            "| Dataset | Version |",
            "|---|---|",
        ]
        for dataset in SOURCE_ORDER:
            lines.append(f"| {dataset} | `{manifest['source_versions'][dataset]}` |")
        lines.extend(
            [
                "",
                "## Output tables",
                "",
                "| Table | Rows | Bytes | SHA-256 |",
                "|---|---:|---:|---|",
            ]
        )
        for table in TABLE_ORDER:
            item = manifest["outputs"][table]
            lines.append(
                f"| {table} | {item['rows']} | {item['size_bytes']} | "
                f"`{item['sha256']}` |"
            )
        lines.extend(
            [
                "",
                "## Validation gates",
                "",
                f"- Source canonical validator: errors={severity['error']}, "
                f"warnings={severity['warning']}, "
                f"informational={severity['informational']}",
                "- Unified JSON Schema validation: passed",
                "- Unified Master PK / ResearchRequirements FK / Coverage: passed",
                "- Source-to-output row preservation: passed",
                "- Source provenance preservation: passed",
                "- Raw/copy source value preservation: passed",
                "- ResearchRequirements duplicate preservation: passed",
                "- Source immutability check during build: passed",
                "",
                "## Scope boundary",
                "",
                "This build generated only the three unified CSV tables, this manifest, "
                "and this summary. It did not generate SQLite, a JSON search index, "
                "Excel, or Site artifacts.",
                "",
            ]
        )
        return "\n".join(lines)

    def _publish(self, publish_dir: Path) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filenames = [
            *(OUTPUT_FILENAMES[table] for table in TABLE_ORDER),
            "build_manifest.json",
            "build_summary.md",
        ]
        backup_dir = publish_dir.parent / "previous"
        backup_dir.mkdir()
        published: list[str] = []
        backed_up: list[str] = []
        try:
            for filename in filenames:
                destination = self.output_dir / filename
                if destination.exists():
                    os.replace(destination, backup_dir / filename)
                    backed_up.append(filename)
                os.replace(publish_dir / filename, destination)
                published.append(filename)
        except Exception:
            for filename in reversed(published):
                destination = self.output_dir / filename
                if destination.exists():
                    destination.unlink()
            for filename in backed_up:
                backup = backup_dir / filename
                if backup.exists():
                    os.replace(backup, self.output_dir / filename)
            raise


def file_metadata(path: Path, repo_root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": str(path.relative_to(repo_root)),
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def portable_manifest_path(path: Path, repo_root: Path) -> str:
    """Prefer a repository-relative manifest path, allowing external outputs."""

    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\r\n", "\n").replace("\r", "\n"))
