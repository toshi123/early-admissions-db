"""Deterministic, read-only SQLite to static Site-data projection build."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import shutil
import sqlite3
import statistics
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator

from .search_qa import QA_SPECS
from .site_search import SearchRequest, logical_key, search_rows
from .structured_search import search_database


SITE_DATA_SCHEMA_VERSION = "0.1"
SITE_DATA_BUILDER_VERSION = "0.1.0"
DEFAULT_DATABASE = Path("data/derived/sqlite/early_admissions_2027.sqlite")
DEFAULT_SQLITE_MANIFEST = Path("data/derived/sqlite/build_manifest.json")
DEFAULT_OUTPUT_DIR = Path("data/derived/site/v0_1")
DEFAULT_QA_REPORT = Path("validation/reports/site_data_qa_v0_1.md")
SCHEMA_PATHS = {
    "manifest": Path("schema/site/site_data_manifest_schema_v0_1.json"),
    "search": Path("schema/site/site_search_row_schema_v0_1.json"),
    "detail": Path("schema/site/site_detail_schema_v0_1.json"),
    "filters": Path("schema/site/site_filter_options_schema_v0_1.json"),
}
SEARCH_TARGET_BYTES = 1_250_000
DETAIL_TARGET_BYTES = 256_000

SEARCH_ADMISSION_FIELDS = (
    "source_dataset",
    "source_version",
    "record_id",
    "institution_type",
    "university",
    "prefecture",
    "faculty_school",
    "department",
    "selection_category",
    "selection_name",
    "slot_type",
    "capacity",
    "academic_field",
    "stem_flag",
    "exclusive_enrollment_status",
    "school_recommendation_required",
    "academic_record_required",
    "common_test_required",
    "research_requirement_required",
    "research_activity_level_status",
    "selection_interview",
    "selection_oral_exam",
    "selection_presentation",
    "selection_essay",
    "selection_written_exam",
    "selection_common_test",
    "gpa_requirement",
    "application_start",
    "application_end",
    "fallback_previous_year",
    "information_year",
    "publication_status",
)

OPTION_FIELDS = (
    ("universities", "university"),
    ("institution_types", "institution_type"),
    ("prefectures", "prefecture"),
    ("raw_academic_fields", "academic_field"),
    ("selection_categories", "selection_category"),
    ("exclusive_enrollment_statuses", "exclusive_enrollment_status"),
    ("school_recommendation_required", "school_recommendation_required"),
    ("academic_record_required", "academic_record_required"),
    ("common_test_required", "common_test_required"),
    ("research_requirement_required", "research_requirement_required"),
    ("research_activity_level_status", "research_activity_level_status"),
)
SELECTION_METHOD_FIELDS = (
    "selection_interview",
    "selection_oral_exam",
    "selection_presentation",
    "selection_essay",
    "selection_written_exam",
    "selection_common_test",
)


class SiteDataBuildError(RuntimeError):
    """Raised when Site-data cannot be safely published."""


@dataclass(frozen=True)
class SiteDataBuildResult:
    output_dir: Path
    manifest_path: Path
    qa_report_path: Path
    build_id: str
    manifest_sha256: str
    counts: Mapping[str, int]
    size_report: Mapping[str, Any]
    validation: Mapping[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _portable_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _next_power_of_two(value: int) -> int:
    return 1 if value <= 1 else 1 << (value - 1).bit_length()


def _shard_count(total_bytes: int, target_bytes: int, row_count: int) -> int:
    if row_count == 0:
        return 1
    return min(row_count, _next_power_of_two(max(1, math.ceil(total_bytes / target_bytes))))


def _bucket(key: tuple[str, str, str], count: int) -> int:
    payload = json.dumps(key, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % count


def _bool_value(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if value not in (0, 1):
        raise SiteDataBuildError(f"{field} is not 0/1/NULL: {value!r}")
    return bool(value)


def _option_label(value: Any) -> str:
    return "—（未記録または非該当）" if value is None else str(value)


class SiteDataBuildPipeline:
    def __init__(
        self,
        repo_root: Path,
        *,
        database_path: Path = DEFAULT_DATABASE,
        sqlite_manifest_path: Path = DEFAULT_SQLITE_MANIFEST,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        qa_report_path: Path = DEFAULT_QA_REPORT,
        build_timestamp_utc: str | None = None,
    ) -> None:
        self.root = repo_root.resolve()
        self.database = self._resolve(database_path)
        self.sqlite_manifest = self._resolve(sqlite_manifest_path)
        self.output_dir = self._resolve(output_dir)
        self.qa_report = self._resolve(qa_report_path)
        self.build_timestamp = build_timestamp_utc or datetime.now(timezone.utc).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z")
        self.schemas = {name: self._resolve(path) for name, path in SCHEMA_PATHS.items()}

    def _resolve(self, path: Path) -> Path:
        return path if path.is_absolute() else self.root / path

    def build(self) -> SiteDataBuildResult:
        before_hash = _sha256(self.database)
        sqlite_manifest_hash = _sha256(self.sqlite_manifest)
        sqlite_manifest = json.loads(self.sqlite_manifest.read_text(encoding="utf-8"))
        self._validate_input_manifest(sqlite_manifest, before_hash)
        schema_documents = self._load_schemas()
        connection = self._open_database()
        try:
            metadata = dict(connection.execute("SELECT * FROM build_metadata").fetchone())
            self._validate_metadata(metadata, sqlite_manifest)
            admissions = [dict(row) for row in connection.execute(
                "SELECT * FROM admissions ORDER BY admission_rowid"
            )]
            gpa = {row["admission_rowid"]: dict(row) for row in connection.execute(
                "SELECT * FROM admission_search_gpa ORDER BY admission_rowid"
            )}
            academic = {row["admission_rowid"]: dict(row) for row in connection.execute(
                "SELECT * FROM admission_search_academic_fields ORDER BY admission_rowid"
            )}
            groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for row in connection.execute(
                "SELECT * FROM admission_search_academic_field_groups "
                "ORDER BY admission_rowid, group_order"
            ):
                groups[row["admission_rowid"]].append(dict(row))
            children: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
            all_children: list[dict[str, Any]] = []
            for row in connection.execute(
                "SELECT * FROM research_requirements ORDER BY research_rowid"
            ):
                item = dict(row)
                all_children.append(item)
                children[(item["source_dataset"], item["source_version"], item["admission_id"])].append(item)
            taxonomy = [dict(row) for row in connection.execute(
                "SELECT * FROM academic_field_taxonomy ORDER BY display_order"
            )]
            search_rows_raw, details = self._project(
                admissions, gpa, academic, groups, children
            )
            build_id = self._build_id(before_hash, metadata)
            search_count = _shard_count(
                sum(len(_json_bytes(row)) for row in search_rows_raw),
                SEARCH_TARGET_BYTES,
                len(search_rows_raw),
            )
            detail_count = _shard_count(
                sum(len(_json_bytes(row)) for row in details),
                DETAIL_TARGET_BYTES,
                len(details),
            )
            for row in search_rows_raw:
                detail_index = _bucket(logical_key(row), detail_count)
                row["detail_path"] = (
                    f"assets/{build_id}/details/details-{detail_index:03d}.json"
                )
            filter_options = self._filter_options(connection, taxonomy, build_id)
            parent = self.output_dir.parent
            parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=".site-data-v0_1-", dir=parent))
            try:
                artifacts, size_report = self._write_assets(
                    staging,
                    build_id,
                    search_rows_raw,
                    details,
                    filter_options,
                    search_count,
                    detail_count,
                )
                validation = self._validate_projection(
                    connection,
                    admissions,
                    all_children,
                    search_rows_raw,
                    details,
                    filter_options,
                    artifacts,
                    staging,
                    schema_documents,
                    sqlite_manifest,
                )
                manifest = self._manifest(
                    before_hash,
                    sqlite_manifest_hash,
                    sqlite_manifest,
                    metadata,
                    build_id,
                    artifacts,
                    search_rows_raw,
                    details,
                    all_children,
                    size_report,
                    validation,
                )
                Draft202012Validator(schema_documents["manifest"]).validate(manifest)
                _write_json(staging / "build_manifest.json", manifest)
                if _sha256(self.database) != before_hash:
                    raise SiteDataBuildError("Input SQLite changed during Site-data build.")
                self._publish(staging)
            except Exception:
                shutil.rmtree(staging, ignore_errors=True)
                raise
        finally:
            connection.close()
        manifest_path = self.output_dir / "build_manifest.json"
        published = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._write_qa_report(published)
        return SiteDataBuildResult(
            output_dir=self.output_dir,
            manifest_path=manifest_path,
            qa_report_path=self.qa_report,
            build_id=published["build_id"],
            manifest_sha256=_sha256(manifest_path),
            counts=published["counts"],
            size_report=published["size_report"],
            validation=published["validation"],
        )

    def _validate_input_manifest(self, manifest: Mapping[str, Any], database_hash: str) -> None:
        if manifest.get("validation", {}).get("status") != "passed":
            raise SiteDataBuildError("SQLite build manifest is not validated/passed.")
        output = manifest.get("output", {})
        if output.get("sha256") != database_hash:
            raise SiteDataBuildError("SQLite SHA-256 does not match its build manifest.")
        if output.get("size_bytes") != self.database.stat().st_size:
            raise SiteDataBuildError("SQLite size does not match its build manifest.")
        if manifest.get("database_schema_version") != "0.1":
            raise SiteDataBuildError("SQLite manifest schema version mismatch.")

    def _load_schemas(self) -> dict[str, Mapping[str, Any]]:
        documents: dict[str, Mapping[str, Any]] = {}
        for name, path in self.schemas.items():
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(document)
            except (OSError, json.JSONDecodeError) as error:
                raise SiteDataBuildError(f"Cannot load Site schema {path}: {error}") from error
            documents[name] = document
        return documents

    def _open_database(self) -> sqlite3.Connection:
        uri = self.database.resolve().as_uri() + "?mode=ro&immutable=1"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
            connection.close()
            raise SiteDataBuildError("SQLite query_only mode could not be enabled.")
        return connection

    def _validate_metadata(
        self, metadata: Mapping[str, Any], manifest: Mapping[str, Any]
    ) -> None:
        expected = {
            "database_schema_version": manifest["database_schema_version"],
            "unified_contract_version": manifest["unified_contract_version"],
            "gpa_parser_contract_version": manifest["gpa_search"]["parser_contract_version"],
            "academic_field_mapping_contract_version": manifest["academic_field_search"]["mapping_contract_version"],
            "academic_field_taxonomy_version": manifest["academic_field_search"]["taxonomy_version"],
        }
        mismatches = {key: (metadata.get(key), value) for key, value in expected.items() if metadata.get(key) != value}
        if mismatches:
            raise SiteDataBuildError(f"SQLite metadata/manifest mismatch: {mismatches}")

    def _project(
        self,
        admissions: Sequence[Mapping[str, Any]],
        gpa: Mapping[int, Mapping[str, Any]],
        academic: Mapping[int, Mapping[str, Any]],
        groups: Mapping[int, list[dict[str, Any]]],
        children: Mapping[tuple[str, str, str], list[dict[str, Any]]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        search_rows: list[dict[str, Any]] = []
        details: list[dict[str, Any]] = []
        for source in admissions:
            admission = dict(source)
            rowid = admission["admission_rowid"]
            if rowid not in gpa or rowid not in academic:
                raise SiteDataBuildError(f"Missing derived parent for admission_rowid={rowid}")
            gpa_row = dict(gpa[rowid])
            academic_row = dict(academic[rowid])
            group_rows = [dict(row) for row in groups.get(rowid, [])]
            key = (admission["source_dataset"], admission["source_version"], admission["record_id"])
            search = {field: admission[field] for field in SEARCH_ADMISSION_FIELDS}
            search["stem_flag"] = _bool_value(search["stem_flag"], "stem_flag")
            search["fallback_previous_year"] = _bool_value(
                search["fallback_previous_year"], "fallback_previous_year"
            )
            search.update(
                {
                    "academic_field_mapping_status": academic_row["mapping_status"],
                    "academic_field_groups": [row["group_code"] for row in group_rows],
                    "academic_field_mapping_contract_version": academic_row["mapping_contract_version"],
                    "gpa_parse_status": gpa_row["parse_status"],
                    "gpa_search_disposition": gpa_row["search_disposition"],
                    "gpa_min_tenths": gpa_row["gpa_min_tenths"],
                    "gpa_min_inclusive": (
                        _bool_value(gpa_row["gpa_min_inclusive"], "gpa_min_inclusive")
                        if gpa_row["gpa_min_inclusive"] is not None
                        else None
                    ),
                    "gpa_max_tenths": gpa_row["gpa_max_tenths"],
                    "gpa_max_inclusive": (
                        _bool_value(gpa_row["gpa_max_inclusive"], "gpa_max_inclusive")
                        if gpa_row["gpa_max_inclusive"] is not None
                        else None
                    ),
                    "gpa_source_value_status": gpa_row["source_value_status"],
                    "detail_path": "",
                }
            )
            search_rows.append(search)
            admission["stem_flag"] = _bool_value(admission["stem_flag"], "stem_flag")
            admission["fallback_previous_year"] = _bool_value(
                admission["fallback_previous_year"], "fallback_previous_year"
            )
            for field in (
                "gpa_min_inclusive",
                "gpa_max_inclusive",
                "has_subject_condition",
                "has_and_condition",
                "has_or_condition",
                "has_branch_condition",
            ):
                if gpa_row[field] is not None:
                    gpa_row[field] = _bool_value(gpa_row[field], field)
            details.append(
                {
                    "site_data_schema_version": SITE_DATA_SCHEMA_VERSION,
                    "identity": dict(zip(("source_dataset", "source_version", "record_id"), key)),
                    "admission": admission,
                    "gpa_derived": gpa_row,
                    "academic_field_derived": {
                        **academic_row,
                        "groups": group_rows,
                    },
                    "research_requirements": [dict(row) for row in children.get(key, [])],
                }
            )
        return search_rows, details

    def _build_id(self, sqlite_hash: str, metadata: Mapping[str, Any]) -> str:
        identity = {
            "sqlite_sha256": sqlite_hash,
            "site_data_schema_version": SITE_DATA_SCHEMA_VERSION,
            "builder_version": SITE_DATA_BUILDER_VERSION,
            "gpa_parser_contract_version": metadata["gpa_parser_contract_version"],
            "academic_field_mapping_contract_version": metadata["academic_field_mapping_contract_version"],
            "academic_field_taxonomy_version": metadata["academic_field_taxonomy_version"],
        }
        return hashlib.sha256(_json_bytes(identity)).hexdigest()[:20]

    def _options_for(self, connection: sqlite3.Connection, field: str) -> list[dict[str, Any]]:
        rows = connection.execute(
            f"SELECT {field} AS value, COUNT(*) AS rows FROM admissions "
            f"GROUP BY {field} ORDER BY {field} IS NOT NULL DESC, {field}"
        ).fetchall()
        return [
            {"value": row["value"], "display_label": _option_label(row["value"]), "unfiltered_count": row["rows"]}
            for row in rows
        ]

    def _filter_options(
        self,
        connection: sqlite3.Connection,
        taxonomy: Sequence[Mapping[str, Any]],
        build_id: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "site_data_schema_version": SITE_DATA_SCHEMA_VERSION,
            "build_id": build_id,
        }
        for option_name, field in OPTION_FIELDS:
            payload[option_name] = self._options_for(connection, field)
        payload["academic_field_mapping_statuses"] = [
            {"value": row["value"], "display_label": str(row["value"]), "unfiltered_count": row["rows"]}
            for row in connection.execute(
                "SELECT mapping_status AS value, COUNT(*) AS rows "
                "FROM admission_search_academic_fields GROUP BY mapping_status ORDER BY mapping_status"
            )
        ]
        group_counts = {row["group_code"]: row["rows"] for row in connection.execute(
            "SELECT group_code, COUNT(*) AS rows FROM admission_search_academic_field_groups GROUP BY group_code"
        )}
        payload["academic_field_groups"] = [
            {
                "value": row["group_code"],
                "display_label": row["display_label"],
                "description": row["description"],
                "display_order": row["display_order"],
                "unfiltered_count": group_counts.get(row["group_code"], 0),
            }
            for row in taxonomy
        ]
        payload["selection_method_values"] = {
            field: self._options_for(connection, field) for field in SELECTION_METHOD_FIELDS
        }
        return payload

    def _write_assets(
        self,
        staging: Path,
        build_id: str,
        search_rows_data: Sequence[Mapping[str, Any]],
        details: Sequence[Mapping[str, Any]],
        filter_options: Mapping[str, Any],
        search_count: int,
        detail_count: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        base = staging / "assets" / build_id
        artifacts: list[dict[str, Any]] = []
        record_sizes = sorted(len(_json_bytes(item)) for item in details)
        search_buckets: list[list[Mapping[str, Any]]] = [[] for _ in range(search_count)]
        detail_buckets: list[list[Mapping[str, Any]]] = [[] for _ in range(detail_count)]
        for row in search_rows_data:
            search_buckets[_bucket(logical_key(row), search_count)].append(row)
        for detail in details:
            detail_buckets[_bucket(logical_key(detail["identity"]), detail_count)].append(detail)
        for bucket_rows in search_buckets:
            bucket_rows.sort(key=logical_key)
        for bucket_rows in detail_buckets:
            bucket_rows.sort(key=lambda item: logical_key(item["identity"]))
        search_bytes = search_gzip = detail_bytes = detail_gzip = 0
        for kind, buckets, directory, stem, rows_key in (
            ("search_shard", search_buckets, "search", "search_rows", "rows"),
            ("detail_shard", detail_buckets, "details", "details", "details"),
        ):
            for index, rows in enumerate(buckets):
                payload = {
                    "site_data_schema_version": SITE_DATA_SCHEMA_VERSION,
                    "build_id": build_id,
                    "shard_index": index,
                    "shard_count": len(buckets),
                    rows_key: rows,
                }
                relative = Path("assets") / build_id / directory / f"{stem}-{index:03d}.json"
                path = staging / relative
                _write_json(path, payload)
                raw = path.read_bytes()
                compressed = gzip.compress(raw, compresslevel=9, mtime=0)
                if kind == "search_shard":
                    search_bytes += len(raw)
                    search_gzip += len(compressed)
                else:
                    detail_bytes += len(raw)
                    detail_gzip += len(compressed)
                artifacts.append(
                    {"kind": kind, "path": relative.as_posix(), "sha256": _sha256(path), "size_bytes": len(raw), "record_count": len(rows)}
                )
        filter_relative = Path("assets") / build_id / "filter_options.json"
        filter_path = staging / filter_relative
        _write_json(filter_path, filter_options)
        artifacts.append(
            {"kind": "filter_options", "path": filter_relative.as_posix(), "sha256": _sha256(filter_path), "size_bytes": filter_path.stat().st_size, "record_count": sum(len(value) for key, value in filter_options.items() if isinstance(value, list))}
        )
        percentile_index = max(0, math.ceil(len(record_sizes) * 0.95) - 1)
        size_report = {
            "search_projection_bytes": search_bytes,
            "search_projection_gzip_bytes": search_gzip,
            "search_shards": search_count,
            "search_average_row_bytes": round(sum(len(_json_bytes(row)) for row in search_rows_data) / max(1, len(search_rows_data)), 2),
            "filter_options_bytes": filter_path.stat().st_size,
            "detail_projection_bytes": detail_bytes,
            "detail_projection_gzip_equivalent_bytes": detail_gzip,
            "detail_shards": detail_count,
            "largest_detail_record_bytes": max(record_sizes, default=0),
            "median_detail_record_bytes": statistics.median(record_sizes) if record_sizes else 0,
            "p95_detail_record_bytes": record_sizes[percentile_index] if record_sizes else 0,
            "generated_file_count_excluding_manifest": len(artifacts),
        }
        return artifacts, size_report

    def _validate_projection(
        self,
        connection: sqlite3.Connection,
        admissions: Sequence[Mapping[str, Any]],
        all_children: Sequence[Mapping[str, Any]],
        search_rows_data: Sequence[Mapping[str, Any]],
        details: Sequence[Mapping[str, Any]],
        filter_options: Mapping[str, Any],
        artifacts: Sequence[Mapping[str, Any]],
        staging: Path,
        schemas: Mapping[str, Mapping[str, Any]],
        sqlite_manifest: Mapping[str, Any],
    ) -> dict[str, Any]:
        search_validator = Draft202012Validator(schemas["search"])
        detail_validator = Draft202012Validator(schemas["detail"])
        filters_validator = Draft202012Validator(schemas["filters"])
        for row in search_rows_data:
            search_validator.validate(row)
        for detail in details:
            detail_validator.validate(detail)
        filters_validator.validate(filter_options)
        admission_keys = [(row["source_dataset"], row["source_version"], row["record_id"]) for row in admissions]
        search_keys = [logical_key(row) for row in search_rows_data]
        detail_keys = [logical_key(row["identity"]) for row in details]
        if not (len(admission_keys) == len(set(admission_keys)) == len(search_keys) == len(detail_keys)):
            raise SiteDataBuildError("Admission/search/detail cardinality or uniqueness failed.")
        if set(admission_keys) != set(search_keys) or set(admission_keys) != set(detail_keys):
            raise SiteDataBuildError("Admission/search/detail logical-key sets differ.")
        detail_by_key = {logical_key(row["identity"]): row for row in details}
        for raw, search in zip(admissions, search_rows_data):
            for field in SEARCH_ADMISSION_FIELDS:
                expected = raw[field]
                if field in {"stem_flag", "fallback_previous_year"}:
                    expected = None if expected is None else bool(expected)
                if search[field] != expected:
                    raise SiteDataBuildError(f"Search raw equality failed for {logical_key(search)} field {field}")
            detail = detail_by_key[logical_key(search)]
            for field, expected in raw.items():
                if field in {"stem_flag", "fallback_previous_year"}:
                    expected = None if expected is None else bool(expected)
                if detail["admission"][field] != expected:
                    raise SiteDataBuildError(f"Detail raw equality failed for {logical_key(search)} field {field}")
            if search["gpa_requirement"] != detail["gpa_derived"]["raw_value"]:
                raise SiteDataBuildError("GPA raw equality failed.")
            if search["academic_field"] != detail["academic_field_derived"]["raw_value"]:
                raise SiteDataBuildError("Academic-field raw equality failed.")
        projected_children = [child for detail in details for child in detail["research_requirements"]]
        source_child_multiset = Counter(_json_bytes(dict(row)) for row in all_children)
        projected_child_multiset = Counter(_json_bytes(dict(row)) for row in projected_children)
        if source_child_multiset != projected_child_multiset:
            raise SiteDataBuildError("ResearchRequirements multiplicity/equality failed.")
        path_keys: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
        detail_shards = sum(item["kind"] == "detail_shard" for item in artifacts)
        for detail in details:
            key = logical_key(detail["identity"])
            index = _bucket(key, detail_shards)
            path = next(
                item["path"]
                for item in artifacts
                if item["kind"] == "detail_shard"
                and Path(item["path"]).stem.endswith(f"-{index:03d}")
            )
            path_keys[path].add(key)
        if any(
            logical_key(row) not in path_keys.get(row["detail_path"], set())
            for row in search_rows_data
        ):
            raise SiteDataBuildError("A search row points to a missing detail record/shard.")
        for item in artifacts:
            path = staging / item["path"]
            if _sha256(path) != item["sha256"] or path.stat().st_size != item["size_bytes"]:
                raise SiteDataBuildError(f"Artifact receipt mismatch: {item['path']}")
        qa = self._equivalence_qa(search_rows_data)
        expected_counts = sqlite_manifest["row_counts"]
        if len(admissions) != expected_counts["admissions"] or len(all_children) != expected_counts["research_requirements"]:
            raise SiteDataBuildError("SQLite projection counts disagree with SQLite manifest.")
        return {
            "status": "passed",
            "input_sqlite_manifest": "passed",
            "readonly_immutable_query_only": "passed",
            "json_schema": "passed",
            "one_search_row_per_admission": "passed",
            "one_detail_per_admission": "passed",
            "logical_key_uniqueness": "passed",
            "raw_and_provenance_equality": "passed",
            "null_boolean_tristate_semantics": "passed",
            "gpa_integer_tenths_preserved": "passed",
            "academic_field_groups_preserved": "passed",
            "research_duplicate_multiplicity": "passed",
            "detail_routes_complete": "passed",
            "artifact_hashes_and_sizes": "passed",
            "search_equivalence": qa,
        }

    def _equivalence_qa(self, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for index, spec in enumerate(QA_SPECS, start=1):
            criteria = spec.criteria
            request = SearchRequest(
                **{name: getattr(criteria, name) for name in SearchRequest.__dataclass_fields__}
            )
            sqlite_result = search_database(self.database, criteria, limit=None)
            site_result = search_rows(rows, request, limit=None)
            sqlite_keys = {logical_key(row) for row in sqlite_result.rows}
            site_keys = {logical_key(row) for row in site_result.rows}
            if sqlite_keys != site_keys:
                raise SiteDataBuildError(f"Search equivalence logical-key mismatch for QA query {index}")
            left, right = sqlite_result.summary, site_result.summary
            comparisons = (
                left.total_matched_rows == right.total_matched_rows,
                dict(left.rows_by_source_dataset) == dict(right.rows_by_source_dataset),
                left.university_count == right.university_count,
                left.gpa_safe_match_rows == right.gpa_safe_match_rows,
                left.gpa_safe_no_match_rows == right.gpa_safe_no_match_rows,
                left.gpa_conditional_review_rows == right.gpa_conditional_review_rows,
                left.gpa_not_numerically_evaluable_rows == right.gpa_not_numerically_evaluable_rows,
            )
            if not all(comparisons):
                raise SiteDataBuildError(f"Search summary mismatch for QA query {index}")
            results.append({"query": index, "label": spec.label, "rows": len(site_keys), "status": "passed"})
        gpa_counts = {}
        for value in (30, 35, 38, 40, 45):
            result = search_rows(rows, SearchRequest(gpa_tenths=value, gpa_mode="safe"), limit=0)
            gpa_counts[f"{value / 10:.1f}"] = result.summary.total_matched_rows
        return {"status": "passed", "queries": len(results), "results": results, "gpa_safe_match_counts": gpa_counts, "comparison": "logical-key set and summary equality"}

    def _manifest(
        self,
        database_hash: str,
        sqlite_manifest_hash: str,
        sqlite_manifest: Mapping[str, Any],
        metadata: Mapping[str, Any],
        build_id: str,
        artifacts: Sequence[Mapping[str, Any]],
        search_rows_data: Sequence[Mapping[str, Any]],
        details: Sequence[Mapping[str, Any]],
        children: Sequence[Mapping[str, Any]],
        size_report: Mapping[str, Any],
        validation: Mapping[str, Any],
    ) -> dict[str, Any]:
        source_counts = Counter(row["source_dataset"] for row in search_rows_data)
        gpa_counts = Counter(row["gpa_search_disposition"] for row in search_rows_data)
        mapping_counts = Counter(row["academic_field_mapping_status"] for row in search_rows_data)
        group_counts = Counter(code for row in search_rows_data for code in row["academic_field_groups"])
        child_factual_counts = Counter(
            _json_bytes({key: value for key, value in row.items() if key != "research_rowid"})
            for row in children
        )
        duplicate_excess = sum(count - 1 for count in child_factual_counts.values())
        return {
            "artifact": "early_admissions_site_data",
            "manifest_version": "1",
            "site_data_schema_version": SITE_DATA_SCHEMA_VERSION,
            "builder_version": SITE_DATA_BUILDER_VERSION,
            "build_timestamp_utc": self.build_timestamp,
            "build_id": build_id,
            "publication": {"status": "published_after_all_validations_passed", "atomic_directory_replacement": True},
            "input": {
                "sqlite_path": _portable_path(self.database, self.root),
                "sqlite_sha256": database_hash,
                "sqlite_size_bytes": self.database.stat().st_size,
                "sqlite_build_manifest_path": _portable_path(self.sqlite_manifest, self.root),
                "sqlite_build_manifest_sha256": sqlite_manifest_hash,
                "sqlite_schema_version": metadata["database_schema_version"],
                "sqlite_builder_version": sqlite_manifest["builder_version"],
                "unified_contract_version": metadata["unified_contract_version"],
                "source_versions": json.loads(metadata["source_versions_json"]),
                "input_csv_sha256": json.loads(metadata["input_csv_sha256_json"]),
                "gpa_parser_contract_version": metadata["gpa_parser_contract_version"],
                "academic_field_mapping_contract_version": metadata["academic_field_mapping_contract_version"],
                "academic_field_taxonomy_version": metadata["academic_field_taxonomy_version"],
                "academic_field_crosswalk_sha256": metadata["academic_field_crosswalk_sha256"],
            },
            "sharding": {
                "algorithm": "sha256(logical-key JSON) modulo next-power-of-two(data-bytes/target-bytes)",
                "search_target_bytes": SEARCH_TARGET_BYTES,
                "detail_target_bytes": DETAIL_TARGET_BYTES,
                "search_shards": size_report["search_shards"],
                "detail_shards": size_report["detail_shards"],
            },
            "outputs": {"artifacts": list(artifacts)},
            "counts": {
                "search_rows": len(search_rows_data),
                "detail_records": len(details),
                "research_requirement_rows": len(children),
                "research_exact_duplicate_excess_rows": duplicate_excess,
                "source_datasets": dict(sorted(source_counts.items())),
                "universities": len({row["university"] for row in search_rows_data}),
                "fallback_rows": sum(row["fallback_previous_year"] is True for row in search_rows_data),
                "gpa_dispositions": dict(sorted(gpa_counts.items())),
                "academic_field_mapping_statuses": dict(sorted(mapping_counts.items())),
                "academic_field_group_memberships": dict(sorted(group_counts.items())),
            },
            "size_report": dict(size_report),
            "validation": dict(validation),
            "scope_boundary": {"generated": ["static Site-data projection"], "not_generated": ["Site UI", "API server", "AI search", "FTS search"]},
        }

    def _publish(self, staging: Path) -> None:
        backup = self.output_dir.with_name(self.output_dir.name + ".previous")
        if backup.exists():
            shutil.rmtree(backup)
        moved_old = False
        try:
            if self.output_dir.exists():
                os.replace(self.output_dir, backup)
                moved_old = True
            os.replace(staging, self.output_dir)
        except Exception:
            if moved_old and backup.exists() and not self.output_dir.exists():
                os.replace(backup, self.output_dir)
            raise
        if backup.exists():
            shutil.rmtree(backup)

    def _write_qa_report(self, manifest: Mapping[str, Any]) -> None:
        counts = manifest["counts"]
        sizes = manifest["size_report"]
        qa = manifest["validation"]["search_equivalence"]
        lines = [
            "# Site-data projection v0.1 QA",
            "",
            f"- Build ID: `{manifest['build_id']}`",
            f"- Input SQLite SHA-256: `{manifest['input']['sqlite_sha256']}`",
            f"- Site-data schema: `{manifest['site_data_schema_version']}`",
            f"- Validation: `{manifest['validation']['status']}`",
            f"- Search rows / detail records / child rows: {counts['search_rows']} / {counts['detail_records']} / {counts['research_requirement_rows']}",
            f"- Search shards / detail shards: {sizes['search_shards']} / {sizes['detail_shards']}",
            f"- Search bytes / gzip equivalent: {sizes['search_projection_bytes']} / {sizes['search_projection_gzip_bytes']}",
            f"- Detail bytes / gzip equivalent: {sizes['detail_projection_bytes']} / {sizes['detail_projection_gzip_equivalent_bytes']}",
            f"- SQLite-to-Site semantic equivalence: {qa['queries']} queries, logical-key set and summary equality PASS",
            "",
            "## GPA strict-safe regression",
            "",
        ]
        for value, count in qa["gpa_safe_match_counts"].items():
            lines.append(f"- GPA {value}: {count}")
        lines.extend(
            [
                "",
                "## Academic-field regression",
                "",
                f"- Mapping statuses: `{json.dumps(counts['academic_field_mapping_statuses'], ensure_ascii=False, sort_keys=True)}`",
                f"- Group memberships: `{json.dumps(counts['academic_field_group_memberships'], ensure_ascii=False, sort_keys=True)}`",
                "",
                "## Scope",
                "",
                "SQLite was opened with `mode=ro&immutable=1` and `PRAGMA query_only=ON`. No Site UI, API, FTS search, conditional-GPA evaluator, date parser, or source-data mutation was performed.",
                "",
            ]
        )
        self.qa_report.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.qa_report.with_suffix(self.qa_report.suffix + ".tmp")
        temporary.write_text("\n".join(lines), encoding="utf-8", newline="")
        os.replace(temporary, self.qa_report)
