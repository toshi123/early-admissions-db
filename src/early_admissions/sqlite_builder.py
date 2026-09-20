"""Build and validate the SQLite v0.1 derived artifact from unified CSVs."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .academic_field import (
    ACADEMIC_FIELD_CROSSWALK_PATH,
    ACADEMIC_FIELD_CROSSWALK_SHA256,
    ACADEMIC_FIELD_DESIGN_PATH,
    ACADEMIC_FIELD_FREEZE_PATH,
    ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION,
    ACADEMIC_FIELD_SCHEMA_PATH,
    ACADEMIC_FIELD_TAXONOMY_PATH,
    ACADEMIC_FIELD_TAXONOMY_SHA256,
    ACADEMIC_FIELD_TAXONOMY_VERSION,
    AcademicFieldCrosswalk,
    AcademicFieldTaxonomy,
)
from .gpa_search import (
    GPA_AUDIT_PATH,
    GPA_DESIGN_PATH,
    GPA_PARSER_CONTRACT_VERSION,
    GPA_SCHEMA_PATH,
    GPACrosswalk,
    GPAParser,
)
from .english_requirement import (
    ENGLISH_REQUIREMENT_CONTRACT_VERSION,
    ENGLISH_REQUIREMENT_CROSSWALK_PATH,
    ENGLISH_REQUIREMENT_DESIGN_PATH,
    ENGLISH_REQUIREMENT_SCHEMA_PATH,
    EnglishRequirementCrosswalk,
)
from .prefecture_search import (
    PREFECTURE_CROSSWALK_PATH, PREFECTURE_CROSSWALK_SHA256,
    PREFECTURE_DESIGN_PATH, PREFECTURE_MAPPING_CONTRACT_VERSION,
    PREFECTURE_SCHEMA_PATH, PREFECTURE_TAXONOMY_PATH,
    PREFECTURE_TAXONOMY_SHA256, PREFECTURE_TAXONOMY_VERSION,
    PrefectureCrosswalk, PrefectureTaxonomy,
)


DEFAULT_OUTPUT_DIR = Path("data/derived/sqlite")
DATABASE_FILENAME = "early_admissions_2027.sqlite"
UNIFIED_DIR = Path("data/canonical/unified")
UNIFIED_MANIFEST = UNIFIED_DIR / "build_manifest.json"
SQLITE_SCHEMA = Path("schema/sqlite/early_admissions_sqlite_schema_v0_1.sql")
SQLITE_DESIGN = Path("docs/sqlite_design_v0_1.md")
DATABASE_SCHEMA_VERSION = "0.1"
BUILDER_VERSION = "0.5.0"
GPA_REGRESSION_TENTHS = (30, 35, 38, 40, 45)

TABLE_ORDER = ("master", "coverage", "research_requirements")
TABLE_FILES = {
    "master": "master.csv",
    "coverage": "coverage.csv",
    "research_requirements": "research_requirements.csv",
}
SQL_TABLES = {
    "master": "admissions",
    "coverage": "coverage",
    "research_requirements": "research_requirements",
}
SURROGATE_COLUMNS = {
    "master": "admission_rowid",
    "coverage": "coverage_rowid",
    "research_requirements": "research_rowid",
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
TRI_STATE_FIELDS = (
    "school_recommendation_required",
    "research_requirement_required",
    "academic_record_required",
    "selection_document_review",
    "selection_interview",
    "selection_oral_exam",
    "selection_presentation",
    "selection_essay",
    "selection_written_exam",
    "selection_practical",
    "selection_group_discussion",
    "selection_aptitude_test",
    "selection_common_test",
)
OPTIONAL_FTS_START = "-- BEGIN OPTIONAL FTS5 PROFILE"
OPTIONAL_FTS_END = "-- END OPTIONAL FTS5 PROFILE"


class SQLiteBuildError(RuntimeError):
    """Raised when a SQLite build gate fails before publication."""


@dataclass(frozen=True)
class SQLiteCapabilities:
    sqlite_version: str
    strict: bool
    fts5: bool
    trigram: bool
    unicode61: bool
    profile: str


@dataclass(frozen=True)
class CSVInput:
    table: str
    path: Path
    header: tuple[str, ...]
    rows: int
    columns: int
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class SQLiteBuildResult:
    database_path: Path
    manifest_path: Path
    summary_path: Path
    database_sha256: str
    database_size_bytes: int
    capabilities: SQLiteCapabilities
    row_counts: Mapping[str, int]
    validation: Mapping[str, Any]


class SQLiteBuildPipeline:
    """Create a fresh SQLite database, validate it, and publish atomically."""

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
        self.database_path = self.output_dir / DATABASE_FILENAME
        self.input_dir = self.repo_root / UNIFIED_DIR
        self.input_manifest_path = self.repo_root / UNIFIED_MANIFEST
        self.schema_path = self.repo_root / SQLITE_SCHEMA
        self.design_path = self.repo_root / SQLITE_DESIGN
        self.gpa_schema_path = self.repo_root / GPA_SCHEMA_PATH
        self.gpa_design_path = self.repo_root / GPA_DESIGN_PATH
        self.gpa_audit_path = self.repo_root / GPA_AUDIT_PATH
        self.academic_field_schema_path = self.repo_root / ACADEMIC_FIELD_SCHEMA_PATH
        self.academic_field_design_path = self.repo_root / ACADEMIC_FIELD_DESIGN_PATH
        self.academic_field_freeze_path = self.repo_root / ACADEMIC_FIELD_FREEZE_PATH
        self.academic_field_taxonomy_path = self.repo_root / ACADEMIC_FIELD_TAXONOMY_PATH
        self.academic_field_crosswalk_path = self.repo_root / ACADEMIC_FIELD_CROSSWALK_PATH
        self.english_requirement_schema_path = self.repo_root / ENGLISH_REQUIREMENT_SCHEMA_PATH
        self.english_requirement_design_path = self.repo_root / ENGLISH_REQUIREMENT_DESIGN_PATH
        self.english_requirement_crosswalk_path = self.repo_root / ENGLISH_REQUIREMENT_CROSSWALK_PATH
        self.prefecture_schema_path = self.repo_root / PREFECTURE_SCHEMA_PATH
        self.prefecture_design_path = self.repo_root / PREFECTURE_DESIGN_PATH
        self.prefecture_taxonomy_path = self.repo_root / PREFECTURE_TAXONOMY_PATH
        self.prefecture_crosswalk_path = self.repo_root / PREFECTURE_CROSSWALK_PATH

    def build(self) -> SQLiteBuildResult:
        """Run all gates and replace published files only after complete success."""

        inputs, unified_manifest, input_manifest_sha = self._preflight_inputs()
        capabilities = self._probe_capabilities()
        if not capabilities.strict:
            raise SQLiteBuildError(
                "The active SQLite library does not support STRICT tables."
            )

        schema_raw = self.schema_path.read_bytes()
        schema_sha = hashlib.sha256(schema_raw).hexdigest()
        gpa_schema_raw = self.gpa_schema_path.read_bytes()
        gpa_schema_sha = hashlib.sha256(gpa_schema_raw).hexdigest()
        gpa_audit_sha = sha256_file(self.gpa_audit_path)
        gpa_crosswalk = GPACrosswalk.load(self.gpa_audit_path)
        academic_field_schema_raw = self.academic_field_schema_path.read_bytes()
        academic_field_schema_sha = hashlib.sha256(
            academic_field_schema_raw
        ).hexdigest()
        academic_field_taxonomy_sha = sha256_file(self.academic_field_taxonomy_path)
        academic_field_crosswalk_sha = sha256_file(self.academic_field_crosswalk_path)
        if academic_field_taxonomy_sha != ACADEMIC_FIELD_TAXONOMY_SHA256:
            raise SQLiteBuildError(
                "Academic-field taxonomy SHA-256 differs from frozen v0.1."
            )
        if academic_field_crosswalk_sha != ACADEMIC_FIELD_CROSSWALK_SHA256:
            raise SQLiteBuildError(
                "Academic-field crosswalk SHA-256 differs from frozen v0.1."
            )
        academic_field_taxonomy = AcademicFieldTaxonomy.load(
            self.academic_field_taxonomy_path
        )
        academic_field_crosswalk = AcademicFieldCrosswalk.load(
            self.academic_field_crosswalk_path, academic_field_taxonomy
        )
        english_requirement_schema_raw = self.english_requirement_schema_path.read_bytes()
        english_requirement_schema_sha = hashlib.sha256(english_requirement_schema_raw).hexdigest()
        english_requirement_crosswalk_sha = sha256_file(self.english_requirement_crosswalk_path)
        english_requirement_crosswalk = EnglishRequirementCrosswalk.load(self.english_requirement_crosswalk_path)
        prefecture_schema_raw = self.prefecture_schema_path.read_bytes()
        prefecture_schema_sha = hashlib.sha256(prefecture_schema_raw).hexdigest()
        prefecture_taxonomy_sha = sha256_file(self.prefecture_taxonomy_path)
        prefecture_crosswalk_sha = sha256_file(self.prefecture_crosswalk_path)
        if prefecture_taxonomy_sha != PREFECTURE_TAXONOMY_SHA256 or prefecture_crosswalk_sha != PREFECTURE_CROSSWALK_SHA256:
            raise SQLiteBuildError("Prefecture taxonomy/crosswalk differs from frozen v0.1.")
        prefecture_taxonomy = PrefectureTaxonomy.load(self.prefecture_taxonomy_path)
        prefecture_crosswalk = PrefectureCrosswalk.load(self.prefecture_crosswalk_path, prefecture_taxonomy)
        design_metadata = file_metadata(self.design_path, self.repo_root)
        schema_metadata = file_metadata(self.schema_path, self.repo_root)
        gpa_design_metadata = file_metadata(self.gpa_design_path, self.repo_root)
        gpa_schema_metadata = file_metadata(self.gpa_schema_path, self.repo_root)
        gpa_audit_metadata = file_metadata(self.gpa_audit_path, self.repo_root)
        academic_field_schema_metadata = file_metadata(
            self.academic_field_schema_path, self.repo_root
        )
        academic_field_design_metadata = file_metadata(
            self.academic_field_design_path, self.repo_root
        )
        academic_field_freeze_metadata = file_metadata(
            self.academic_field_freeze_path, self.repo_root
        )
        academic_field_taxonomy_metadata = file_metadata(
            self.academic_field_taxonomy_path, self.repo_root
        )
        academic_field_crosswalk_metadata = file_metadata(
            self.academic_field_crosswalk_path, self.repo_root
        )
        english_requirement_schema_metadata = file_metadata(self.english_requirement_schema_path, self.repo_root)
        english_requirement_design_metadata = file_metadata(self.english_requirement_design_path, self.repo_root)
        english_requirement_crosswalk_metadata = file_metadata(self.english_requirement_crosswalk_path, self.repo_root)
        prefecture_schema_metadata = file_metadata(self.prefecture_schema_path, self.repo_root)
        prefecture_design_metadata = file_metadata(self.prefecture_design_path, self.repo_root)
        prefecture_taxonomy_metadata = file_metadata(self.prefecture_taxonomy_path, self.repo_root)
        prefecture_crosswalk_metadata = file_metadata(self.prefecture_crosswalk_path, self.repo_root)
        source_versions = self._source_versions(unified_manifest)
        self.output_dir.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix=".sqlite-build-", dir=self.output_dir.parent
        ) as temporary:
            work_root = Path(temporary)
            work_database = work_root / DATABASE_FILENAME
            connection: sqlite3.Connection | None = None
            try:
                connection = sqlite3.connect(work_database)
                connection.row_factory = sqlite3.Row
                self._configure_connection(connection)
                connection.executescript(
                    self._schema_for_profile(
                        schema_raw.decode("utf-8"), capabilities.profile
                    )
                )
                connection.executescript(gpa_schema_raw.decode("utf-8"))
                connection.executescript(academic_field_schema_raw.decode("utf-8"))
                connection.executescript(english_requirement_schema_raw.decode("utf-8"))
                connection.executescript(prefecture_schema_raw.decode("utf-8"))
                self._assert_schema_columns(connection, inputs)
                self._load_base_tables(connection, inputs)
                gpa_build = self._load_gpa_layer(connection, gpa_crosswalk)
                academic_field_build = self._load_academic_field_layer(
                    connection,
                    academic_field_taxonomy,
                    academic_field_crosswalk,
                )
                english_requirement_build = self._load_english_requirement_layer(
                    connection, english_requirement_crosswalk
                )
                prefecture_build = self._load_prefecture_layer(connection, prefecture_taxonomy, prefecture_crosswalk)
                built_at = utc_timestamp()
                self._insert_build_metadata(
                    connection,
                    inputs=inputs,
                    unified_manifest=unified_manifest,
                    input_manifest_sha=input_manifest_sha,
                    schema_sha=schema_sha,
                    gpa_schema_sha=gpa_schema_sha,
                    gpa_audit_sha=gpa_audit_sha,
                    gpa_build=gpa_build,
                    academic_field_schema_sha=academic_field_schema_sha,
                    academic_field_taxonomy_sha=academic_field_taxonomy_sha,
                    academic_field_crosswalk_sha=academic_field_crosswalk_sha,
                    academic_field_build=academic_field_build,
                    english_requirement_schema_sha=english_requirement_schema_sha,
                    english_requirement_crosswalk_sha=english_requirement_crosswalk_sha,
                    english_requirement_build=english_requirement_build,
                    prefecture_schema_sha=prefecture_schema_sha,
                    prefecture_taxonomy_sha=prefecture_taxonomy_sha,
                    prefecture_crosswalk_sha=prefecture_crosswalk_sha,
                    prefecture_build=prefecture_build,
                    capabilities=capabilities,
                    built_at=built_at,
                    source_versions=source_versions,
                )
                connection.commit()
                connection.execute("ANALYZE")
                connection.execute("PRAGMA optimize")
                connection.commit()
                validation = self._validate_database(
                    connection,
                    inputs=inputs,
                    unified_manifest=unified_manifest,
                    input_manifest_sha=input_manifest_sha,
                    schema_sha=schema_sha,
                    gpa_schema_sha=gpa_schema_sha,
                    gpa_audit_sha=gpa_audit_sha,
                    gpa_build=gpa_build,
                    academic_field_schema_sha=academic_field_schema_sha,
                    academic_field_taxonomy_sha=academic_field_taxonomy_sha,
                    academic_field_crosswalk_sha=academic_field_crosswalk_sha,
                    academic_field_build=academic_field_build,
                    english_requirement_schema_sha=english_requirement_schema_sha,
                    english_requirement_crosswalk_sha=english_requirement_crosswalk_sha,
                    english_requirement_build=english_requirement_build,
                    prefecture_schema_sha=prefecture_schema_sha,
                    prefecture_taxonomy_sha=prefecture_taxonomy_sha,
                    prefecture_crosswalk_sha=prefecture_crosswalk_sha,
                    prefecture_build=prefecture_build,
                    capabilities=capabilities,
                    built_at=built_at,
                    source_versions=source_versions,
                )
                validation["input_preflight"] = {
                    "status": "passed",
                    "unified_build_manifest_sha256": input_manifest_sha,
                    "csv_sha256": {
                        TABLE_FILES[table]: inputs[table].sha256
                        for table in TABLE_ORDER
                    },
                    "rows": {
                        SQL_TABLES[table]: inputs[table].rows
                        for table in TABLE_ORDER
                    },
                }
                self._assert_inputs_unchanged(
                    inputs,
                    input_manifest_sha=input_manifest_sha,
                    schema_sha=schema_sha,
                    design_sha=design_metadata["sha256"],
                    gpa_schema_sha=gpa_schema_sha,
                    gpa_design_sha=gpa_design_metadata["sha256"],
                    gpa_audit_sha=gpa_audit_sha,
                    academic_field_schema_sha=academic_field_schema_sha,
                    academic_field_design_sha=academic_field_design_metadata["sha256"],
                    academic_field_freeze_sha=academic_field_freeze_metadata["sha256"],
                    academic_field_taxonomy_sha=academic_field_taxonomy_sha,
                    academic_field_crosswalk_sha=academic_field_crosswalk_sha,
                    english_requirement_schema_sha=english_requirement_schema_sha,
                    english_requirement_design_sha=english_requirement_design_metadata["sha256"],
                    english_requirement_crosswalk_sha=english_requirement_crosswalk_sha,
                    prefecture_schema_sha=prefecture_schema_sha,
                    prefecture_design_sha=prefecture_design_metadata["sha256"],
                    prefecture_taxonomy_sha=prefecture_taxonomy_sha,
                    prefecture_crosswalk_sha=prefecture_crosswalk_sha,
                )
                validation["inputs_unchanged_during_build"] = True
                connection.commit()
            except (csv.Error, json.JSONDecodeError, sqlite3.Error, ValueError) as error:
                if connection is not None:
                    connection.rollback()
                raise SQLiteBuildError(f"SQLite build failed: {error}") from error
            finally:
                if connection is not None:
                    connection.close()

            self._assert_no_sidecars(work_database)
            database_sha = sha256_file(work_database)
            database_size = work_database.stat().st_size
            row_counts = {
                SQL_TABLES[table]: inputs[table].rows for table in TABLE_ORDER
            }
            manifest = self._build_manifest(
                inputs=inputs,
                unified_manifest=unified_manifest,
                input_manifest_sha=input_manifest_sha,
                schema_metadata=schema_metadata,
                design_metadata=design_metadata,
                gpa_schema_metadata=gpa_schema_metadata,
                gpa_design_metadata=gpa_design_metadata,
                gpa_audit_metadata=gpa_audit_metadata,
                gpa_build=gpa_build,
                academic_field_schema_metadata=academic_field_schema_metadata,
                academic_field_design_metadata=academic_field_design_metadata,
                academic_field_freeze_metadata=academic_field_freeze_metadata,
                academic_field_taxonomy_metadata=academic_field_taxonomy_metadata,
                academic_field_crosswalk_metadata=academic_field_crosswalk_metadata,
                academic_field_build=academic_field_build,
                english_requirement_schema_metadata=english_requirement_schema_metadata,
                english_requirement_design_metadata=english_requirement_design_metadata,
                english_requirement_crosswalk_metadata=english_requirement_crosswalk_metadata,
                english_requirement_build=english_requirement_build,
                prefecture_schema_metadata=prefecture_schema_metadata,
                prefecture_design_metadata=prefecture_design_metadata,
                prefecture_taxonomy_metadata=prefecture_taxonomy_metadata,
                prefecture_crosswalk_metadata=prefecture_crosswalk_metadata,
                prefecture_build=prefecture_build,
                capabilities=capabilities,
                built_at=built_at,
                row_counts=row_counts,
                validation=validation,
                database_sha=database_sha,
                database_size=database_size,
            )

            publish_dir = work_root / "publish"
            publish_dir.mkdir()
            shutil.copyfile(work_database, publish_dir / DATABASE_FILENAME)
            write_text_lf(
                publish_dir / "build_manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
            )
            write_text_lf(
                publish_dir / "build_summary.md", self._build_summary(manifest)
            )
            self._publish(publish_dir)

        return SQLiteBuildResult(
            database_path=self.database_path,
            manifest_path=self.output_dir / "build_manifest.json",
            summary_path=self.output_dir / "build_summary.md",
            database_sha256=database_sha,
            database_size_bytes=database_size,
            capabilities=capabilities,
            row_counts=row_counts,
            validation=validation,
        )

    def _preflight_inputs(
        self,
    ) -> tuple[dict[str, CSVInput], dict[str, Any], str]:
        required = (
            self.input_manifest_path,
            self.schema_path,
            self.design_path,
            self.gpa_schema_path,
            self.gpa_design_path,
            self.gpa_audit_path,
            self.academic_field_schema_path,
            self.academic_field_design_path,
            self.academic_field_freeze_path,
            self.academic_field_taxonomy_path,
            self.academic_field_crosswalk_path,
            *(self.input_dir / TABLE_FILES[table] for table in TABLE_ORDER),
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise SQLiteBuildError(f"Missing required input(s): {', '.join(missing)}")

        try:
            manifest_raw = self.input_manifest_path.read_bytes()
            manifest = json.loads(manifest_raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SQLiteBuildError(f"Invalid unified build manifest: {error}") from error
        if manifest.get("artifact") != "early_admissions_unified":
            raise SQLiteBuildError("Unified manifest artifact identifier is invalid.")
        if manifest.get("contract_version") != "0.1":
            raise SQLiteBuildError("Unified manifest contract_version is not 0.1.")
        if manifest.get("validation", {}).get("status") != "passed":
            raise SQLiteBuildError("Unified manifest validation status is not passed.")

        outputs = manifest.get("outputs")
        if not isinstance(outputs, dict):
            raise SQLiteBuildError("Unified manifest outputs must be an object.")
        inputs: dict[str, CSVInput] = {}
        for table in TABLE_ORDER:
            metadata = outputs.get(table)
            if not isinstance(metadata, dict):
                raise SQLiteBuildError(f"Unified manifest output missing: {table}")
            path = self.input_dir / TABLE_FILES[table]
            actual = inspect_csv(path, table)
            expected_path = metadata.get("path")
            if expected_path != portable_manifest_path(path, self.repo_root):
                raise SQLiteBuildError(
                    f"Unified manifest path mismatch for {table}: {expected_path!r}"
                )
            checks = {
                "sha256": actual.sha256,
                "size_bytes": actual.size_bytes,
                "rows": actual.rows,
                "columns": actual.columns,
            }
            for field, value in checks.items():
                if metadata.get(field) != value:
                    raise SQLiteBuildError(
                        f"Unified input {field} mismatch for {path.name}: "
                        f"manifest={metadata.get(field)!r}, actual={value!r}"
                    )
            inputs[table] = actual

        self._validate_manifest_redundancy(manifest, inputs)
        return inputs, manifest, hashlib.sha256(manifest_raw).hexdigest()

    @staticmethod
    def _validate_manifest_redundancy(
        manifest: Mapping[str, Any], inputs: Mapping[str, CSVInput]
    ) -> None:
        validation = manifest.get("validation", {})
        unified = validation.get("unified", {})
        expected_counts = {table: inputs[table].rows for table in TABLE_ORDER}
        row_preservation = unified.get("row_preservation", {})
        for key in ("expected_output_rows", "input_rows", "output_rows"):
            declared = row_preservation.get(key)
            if declared is not None and declared != expected_counts:
                raise SQLiteBuildError(
                    f"Unified manifest {key} is inconsistent with its outputs."
                )
        validated_rows = unified.get("json_schema", {}).get("validated_rows")
        if validated_rows is not None and validated_rows != expected_counts:
            raise SQLiteBuildError(
                "Unified manifest JSON Schema row counts are inconsistent."
            )
        declared_hashes = validation.get("determinism", {}).get("sha256")
        expected_hashes = {table: inputs[table].sha256 for table in TABLE_ORDER}
        if declared_hashes is not None and declared_hashes != expected_hashes:
            raise SQLiteBuildError(
                "Unified manifest deterministic hashes are inconsistent."
            )

    def _assert_inputs_unchanged(
        self,
        inputs: Mapping[str, CSVInput],
        *,
        input_manifest_sha: str,
        schema_sha: str,
        design_sha: str,
        gpa_schema_sha: str,
        gpa_design_sha: str,
        gpa_audit_sha: str,
        academic_field_schema_sha: str,
        academic_field_design_sha: str,
        academic_field_freeze_sha: str,
        academic_field_taxonomy_sha: str,
        academic_field_crosswalk_sha: str,
        english_requirement_schema_sha: str,
        english_requirement_design_sha: str,
        english_requirement_crosswalk_sha: str,
        prefecture_schema_sha: str,
        prefecture_design_sha: str,
        prefecture_taxonomy_sha: str,
        prefecture_crosswalk_sha: str,
    ) -> None:
        for table in TABLE_ORDER:
            if sha256_file(inputs[table].path) != inputs[table].sha256:
                raise SQLiteBuildError(
                    f"Unified input changed during build: {inputs[table].path}"
                )
        checks = (
            (self.input_manifest_path, input_manifest_sha),
            (self.schema_path, schema_sha),
            (self.design_path, design_sha),
            (self.gpa_schema_path, gpa_schema_sha),
            (self.gpa_design_path, gpa_design_sha),
            (self.gpa_audit_path, gpa_audit_sha),
            (self.academic_field_schema_path, academic_field_schema_sha),
            (self.academic_field_design_path, academic_field_design_sha),
            (self.academic_field_freeze_path, academic_field_freeze_sha),
            (self.academic_field_taxonomy_path, academic_field_taxonomy_sha),
            (self.academic_field_crosswalk_path, academic_field_crosswalk_sha),
            (self.english_requirement_schema_path, english_requirement_schema_sha),
            (self.english_requirement_design_path, english_requirement_design_sha),
            (self.english_requirement_crosswalk_path, english_requirement_crosswalk_sha),
            (self.prefecture_schema_path, prefecture_schema_sha),
            (self.prefecture_design_path, prefecture_design_sha),
            (self.prefecture_taxonomy_path, prefecture_taxonomy_sha),
            (self.prefecture_crosswalk_path, prefecture_crosswalk_sha),
        )
        for path, expected in checks:
            if sha256_file(path) != expected:
                raise SQLiteBuildError(f"Build contract changed during build: {path}")

    @staticmethod
    def _source_versions(manifest: Mapping[str, Any]) -> dict[str, str]:
        versions = manifest.get("source_versions")
        if not isinstance(versions, dict) or not versions:
            raise SQLiteBuildError("Unified manifest source_versions is invalid.")
        result = {str(key): str(value) for key, value in versions.items()}
        if any(not key or not value for key, value in result.items()):
            raise SQLiteBuildError("Unified manifest contains an empty source version.")
        return dict(sorted(result.items()))

    def _probe_capabilities(self) -> SQLiteCapabilities:
        connection = sqlite3.connect(":memory:")
        strict = fts5 = trigram = unicode61 = False
        try:
            try:
                connection.execute("CREATE TABLE strict_probe(value TEXT) STRICT")
                strict = True
            except sqlite3.Error:
                strict = False
            try:
                connection.execute("CREATE VIRTUAL TABLE fts_probe USING fts5(value)")
                fts5 = True
                connection.execute("DROP TABLE fts_probe")
            except sqlite3.Error:
                fts5 = False
            if fts5:
                trigram = probe_tokenizer(connection, "trigram", "都立大学", "都立大")
                unicode61 = probe_tokenizer(
                    connection, "unicode61", "東京都立大学", "東京都立大学"
                )
        finally:
            connection.close()
        profile = "trigram" if trigram else "unicode61" if unicode61 else "none"
        return SQLiteCapabilities(
            sqlite_version=sqlite3.sqlite_version,
            strict=strict,
            fts5=fts5,
            trigram=trigram,
            unicode61=unicode61,
            profile=profile,
        )

    @staticmethod
    def _configure_connection(connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise SQLiteBuildError("PRAGMA foreign_keys could not be enabled.")
        journal_mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        if str(journal_mode).lower() != "delete":
            raise SQLiteBuildError(f"Unexpected journal mode: {journal_mode}")
        connection.execute("PRAGMA synchronous=FULL")

    @staticmethod
    def _schema_for_profile(schema: str, profile: str) -> str:
        if schema.count(OPTIONAL_FTS_START) != 1 or schema.count(OPTIONAL_FTS_END) != 1:
            raise SQLiteBuildError("Optional FTS profile markers are invalid.")
        before, marked = schema.split(OPTIONAL_FTS_START, 1)
        block, after = marked.split(OPTIONAL_FTS_END, 1)
        if profile == "trigram":
            selected = block
        elif profile == "unicode61":
            if block.count("tokenize = 'trigram'") != 1:
                raise SQLiteBuildError("Expected trigram tokenizer declaration not found.")
            selected = block.replace("tokenize = 'trigram'", "tokenize = 'unicode61'")
        elif profile == "none":
            selected = "\n-- Optional FTS5 objects omitted by portable profile.\n"
        else:
            raise SQLiteBuildError(f"Unsupported SQLite profile: {profile}")
        return before + OPTIONAL_FTS_START + selected + OPTIONAL_FTS_END + after

    @staticmethod
    def _assert_schema_columns(
        connection: sqlite3.Connection, inputs: Mapping[str, CSVInput]
    ) -> None:
        for table in TABLE_ORDER:
            sql_table = SQL_TABLES[table]
            actual = tuple(
                row[1]
                for row in connection.execute(f'PRAGMA table_xinfo("{sql_table}")')
                if row[1] != SURROGATE_COLUMNS[table]
            )
            if actual != inputs[table].header:
                raise SQLiteBuildError(
                    f"Schema/CSV column order mismatch for {table}: "
                    f"schema={actual!r}, csv={inputs[table].header!r}"
                )

    def _load_base_tables(
        self, connection: sqlite3.Connection, inputs: Mapping[str, CSVInput]
    ) -> None:
        connection.execute("BEGIN")
        for table in TABLE_ORDER:
            header = inputs[table].header
            column_sql = ", ".join(quote_identifier(column) for column in header)
            placeholders = ", ".join("?" for _ in header)
            sql = (
                f"INSERT INTO {quote_identifier(SQL_TABLES[table])} "
                f"({column_sql}) VALUES ({placeholders})"
            )
            connection.executemany(sql, self._iter_typed_rows(inputs[table]))

    @staticmethod
    def _load_gpa_layer(
        connection: sqlite3.Connection, crosswalk: GPACrosswalk
    ) -> dict[str, Any]:
        parser = GPAParser(crosswalk)
        insert_sql = """
            INSERT INTO admission_search_gpa (
                admission_rowid, raw_value,
                gpa_min_tenths, gpa_min_inclusive,
                gpa_max_tenths, gpa_max_inclusive,
                gpa_scale, metric_scope, gpa_condition_type,
                parse_status, search_disposition, source_value_status,
                has_subject_condition, has_and_condition,
                has_or_condition, has_branch_condition,
                parser_contract_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        parsed_rows: list[tuple[Any, ...]] = []
        classification_counts: Counter[str] = Counter()
        safe_minima: list[int] = []
        unparsed_record_ids: list[str] = []
        rows = connection.execute(
            """
            SELECT admission_rowid, source_dataset, source_version, record_id,
                   admission_year, gpa_requirement, information_year,
                   fallback_previous_year
            FROM admissions ORDER BY admission_rowid
            """
        )
        for row in rows:
            result = parser.parse(
                row["gpa_requirement"],
                admission_year=row["admission_year"],
                information_year=row["information_year"],
                fallback_previous_year=row["fallback_previous_year"],
            )
            classification_counts[result.numeric_safety_tier] += 1
            if result.gpa_min_tenths is not None:
                safe_minima.append(result.gpa_min_tenths)
            if result.parse_status == "unparsed" and len(unparsed_record_ids) < 10:
                unparsed_record_ids.append(
                    f"{row['source_dataset']}:{row['source_version']}:{row['record_id']}"
                )
            parsed_rows.append(result.sqlite_values(row["admission_rowid"]))
        connection.executemany(insert_sql, parsed_rows)
        match_counts = {
            f"{tenths / 10:.1f}": sum(
                minimum <= tenths for minimum in safe_minima
            )
            for tenths in GPA_REGRESSION_TENTHS
        }
        return {
            "parser_contract_version": GPA_PARSER_CONTRACT_VERSION,
            "crosswalk_distinct_raw_values": len(crosswalk),
            "classification_counts": {
                tier: classification_counts.get(tier, 0)
                for tier in (
                    "safe_numeric",
                    "conditional_numeric",
                    "do_not_numeric",
                )
            },
            "safe_match_counts": match_counts,
            "rule_group_rows": 0,
            "clause_rows": 0,
            "representative_unparsed_record_ids": unparsed_record_ids,
        }

    @staticmethod
    def _load_academic_field_layer(
        connection: sqlite3.Connection,
        taxonomy: AcademicFieldTaxonomy,
        crosswalk: AcademicFieldCrosswalk,
    ) -> dict[str, Any]:
        """Load only exact crosswalk results; no text inference is permitted."""

        connection.executemany(
            """
            INSERT INTO academic_field_taxonomy (
                group_code, display_label, description, display_order,
                taxonomy_version
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                (
                    group.group_code,
                    group.display_label,
                    group.description,
                    group.display_order,
                    ACADEMIC_FIELD_TAXONOMY_VERSION,
                )
                for group in taxonomy
            ),
        )
        parent_rows: list[tuple[Any, ...]] = []
        child_rows: list[tuple[Any, ...]] = []
        classification_counts: Counter[str] = Counter()
        membership_counts: Counter[str] = Counter()
        input_raw_counts: Counter[str] = Counter()
        review_required_raw_counts: Counter[str] = Counter()
        unmapped_raw_counts: Counter[str] = Counter()
        representative_unmapped_record_ids: list[str] = []
        rows = connection.execute(
            """
            SELECT admission_rowid, source_dataset, source_version, record_id,
                   academic_field
            FROM admissions ORDER BY admission_rowid
            """
        )
        for row in rows:
            raw_value = row["academic_field"]
            if raw_value is not None:
                input_raw_counts[raw_value] += 1
            mapping = crosswalk.lookup(raw_value)
            classification_counts[mapping.mapping_status] += 1
            if mapping.mapping_status == "review_required" and raw_value is not None:
                review_required_raw_counts[raw_value] += 1
            if mapping.mapping_status == "unmapped" and raw_value is not None:
                unmapped_raw_counts[raw_value] += 1
            if (
                mapping.mapping_status == "unmapped"
                and len(representative_unmapped_record_ids) < 10
            ):
                representative_unmapped_record_ids.append(
                    f"{row['source_dataset']}:{row['source_version']}:{row['record_id']}"
                )
            parent_rows.append(
                (
                    row["admission_rowid"],
                    raw_value,
                    mapping.mapping_status,
                    mapping.mapping_contract_version,
                    mapping.review_note,
                )
            )
            for group_order, group_code in enumerate(mapping.group_codes, start=1):
                membership_counts[group_code] += 1
                child_rows.append(
                    (
                        row["admission_rowid"],
                        group_code,
                        group_order,
                        "exact_crosswalk",
                    )
                )
        connection.executemany(
            """
            INSERT INTO admission_search_academic_fields (
                admission_rowid, raw_value, mapping_status,
                mapping_contract_version, review_note
            ) VALUES (?, ?, ?, ?, ?)
            """,
            parent_rows,
        )
        connection.executemany(
            """
            INSERT INTO admission_search_academic_field_groups (
                admission_rowid, group_code, group_order, mapping_basis
            ) VALUES (?, ?, ?, ?)
            """,
            child_rows,
        )
        frozen_status_counts = Counter(
            mapping.mapping_status for mapping in crosswalk
        )
        return {
            "mapping_contract_version": ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION,
            "taxonomy_version": ACADEMIC_FIELD_TAXONOMY_VERSION,
            "taxonomy_groups": len(taxonomy),
            "crosswalk_distinct_raw_values": len(crosswalk),
            "crosswalk_mapping_status_counts": {
                status: frozen_status_counts.get(status, 0)
                for status in ("single", "multi", "review_required")
            },
            "input_distinct_non_null_raw_values": len(input_raw_counts),
            "classification_counts": {
                status: classification_counts.get(status, 0)
                for status in (
                    "single",
                    "multi",
                    "review_required",
                    "unmapped",
                    "not_applicable",
                )
            },
            "parent_rows": len(parent_rows),
            "group_rows": len(child_rows),
            "group_membership_counts": {
                group.group_code: membership_counts.get(group.group_code, 0)
                for group in taxonomy
            },
            "raw_mismatch_rows": 0,
            "review_required_raw_value_counts": dict(
                sorted(review_required_raw_counts.items())
            ),
            "unmapped_raw_value_counts": dict(sorted(unmapped_raw_counts.items())),
            "representative_unmapped_record_ids": representative_unmapped_record_ids,
        }

    def _iter_typed_rows(self, item: CSVInput) -> Iterator[tuple[Any, ...]]:
        with item.path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = tuple(next(reader))
            except StopIteration as error:
                raise SQLiteBuildError(f"CSV has no header: {item.path}") from error
            if header != item.header:
                raise SQLiteBuildError(f"CSV header changed during build: {item.path}")
            for line_number, row in enumerate(reader, start=2):
                if len(row) != len(header):
                    raise SQLiteBuildError(
                        f"CSV row width mismatch at {item.path}:{line_number}"
                    )
                yield tuple(
                    convert_csv_value(item.table, field, raw, line_number)
                    for field, raw in zip(header, row)
                )

    @staticmethod
    def _load_english_requirement_layer(
        connection: sqlite3.Connection,
        crosswalk: EnglishRequirementCrosswalk,
    ) -> dict[str, Any]:
        counts: Counter[str] = Counter()
        values: list[tuple[object, ...]] = []
        for row in connection.execute(
            "SELECT admission_rowid, english_requirement FROM admissions ORDER BY admission_rowid"
        ):
            result = crosswalk.classify(row["english_requirement"])
            counts[result.requirement_status] += 1
            values.append(result.sqlite_values(row["admission_rowid"]))
        connection.executemany(
            """
            INSERT INTO admission_search_english_requirement (
                admission_rowid, raw_value, requirement_status, parse_status,
                search_disposition, parser_contract_version, review_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return {
            "parser_contract_version": ENGLISH_REQUIREMENT_CONTRACT_VERSION,
            "crosswalk_distinct_raw_values": len(crosswalk),
            "classification_counts": {
                status: counts.get(status, 0)
                for status in (
                    "required", "not_required", "review_required", "unknown",
                    "not_applicable", "unmapped"
                )
            },
            "raw_mismatch_rows": 0,
        }

    @staticmethod
    def _load_prefecture_layer(connection: sqlite3.Connection, taxonomy: PrefectureTaxonomy, crosswalk: PrefectureCrosswalk) -> dict[str, Any]:
        connection.executemany(
            "INSERT INTO prefecture_taxonomy VALUES (?, ?, ?, ?, ?)",
            ((x.code,x.label,x.region,x.display_order,PREFECTURE_TAXONOMY_VERSION) for x in taxonomy),
        )
        parents=[]; children=[]; counts:Counter[str]=Counter(); memberships:Counter[str]=Counter()
        for row in connection.execute("SELECT admission_rowid,prefecture FROM admissions ORDER BY admission_rowid"):
            mapping=crosswalk.lookup(row["prefecture"]); counts[mapping.mapping_status]+=1
            parents.append((row["admission_rowid"],mapping.raw_value,mapping.mapping_status,PREFECTURE_MAPPING_CONTRACT_VERSION,mapping.review_note))
            for order,code in enumerate(mapping.codes,1):
                label=taxonomy.by_code[code].label; memberships[label]+=1
                children.append((row["admission_rowid"],code,label,order,"exact_crosswalk"))
        connection.executemany("INSERT INTO admission_search_prefectures VALUES (?, ?, ?, ?, ?)",parents)
        connection.executemany("INSERT INTO admission_search_prefecture_memberships VALUES (?, ?, ?, ?, ?)",children)
        return {"mapping_contract_version":PREFECTURE_MAPPING_CONTRACT_VERSION,"taxonomy_version":PREFECTURE_TAXONOMY_VERSION,"crosswalk_distinct_raw_values":len(crosswalk),"parent_rows":len(parents),"membership_rows":len(children),"classification_counts":{s:counts.get(s,0) for s in ("single","multi","review_required","unmapped","not_applicable")},"membership_counts":dict(sorted(memberships.items())),"raw_mismatch_rows":0}

    @staticmethod
    def _insert_build_metadata(
        connection: sqlite3.Connection,
        *,
        inputs: Mapping[str, CSVInput],
        unified_manifest: Mapping[str, Any],
        input_manifest_sha: str,
        schema_sha: str,
        gpa_schema_sha: str,
        gpa_audit_sha: str,
        gpa_build: Mapping[str, Any],
        academic_field_schema_sha: str,
        academic_field_taxonomy_sha: str,
        academic_field_crosswalk_sha: str,
        academic_field_build: Mapping[str, Any],
        english_requirement_schema_sha: str,
        english_requirement_crosswalk_sha: str,
        english_requirement_build: Mapping[str, Any],
        prefecture_schema_sha: str,
        prefecture_taxonomy_sha: str,
        prefecture_crosswalk_sha: str,
        prefecture_build: Mapping[str, Any],
        capabilities: SQLiteCapabilities,
        built_at: str,
        source_versions: Mapping[str, str],
    ) -> None:
        hashes = {TABLE_FILES[table]: inputs[table].sha256 for table in TABLE_ORDER}
        values = (
            1,
            DATABASE_SCHEMA_VERSION,
            unified_manifest["contract_version"],
            unified_manifest["schema_id"],
            built_at,
            BUILDER_VERSION,
            capabilities.sqlite_version,
            int(capabilities.profile != "none"),
            capabilities.profile,
            canonical_json(source_versions),
            canonical_json(hashes),
            input_manifest_sha,
            schema_sha,
            GPA_PARSER_CONTRACT_VERSION,
            gpa_schema_sha,
            gpa_audit_sha,
            ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION,
            ACADEMIC_FIELD_TAXONOMY_VERSION,
            academic_field_schema_sha,
            academic_field_taxonomy_sha,
            academic_field_crosswalk_sha,
            ENGLISH_REQUIREMENT_CONTRACT_VERSION,
            english_requirement_schema_sha,
            english_requirement_crosswalk_sha,
            english_requirement_build["classification_counts"]["required"],
            english_requirement_build["classification_counts"]["not_required"],
            english_requirement_build["classification_counts"]["review_required"],
            english_requirement_build["classification_counts"]["unknown"],
            english_requirement_build["classification_counts"]["not_applicable"],
            english_requirement_build["classification_counts"]["unmapped"],
            PREFECTURE_MAPPING_CONTRACT_VERSION,
            PREFECTURE_TAXONOMY_VERSION,
            prefecture_schema_sha,
            prefecture_taxonomy_sha,
            prefecture_crosswalk_sha,
            prefecture_build["parent_rows"],
            prefecture_build["membership_rows"],
            prefecture_build["classification_counts"]["single"],
            prefecture_build["classification_counts"]["multi"],
            prefecture_build["classification_counts"]["unmapped"],
            inputs["master"].rows,
            inputs["coverage"].rows,
            inputs["research_requirements"].rows,
            gpa_build["classification_counts"]["safe_numeric"],
            gpa_build["classification_counts"]["conditional_numeric"],
            gpa_build["classification_counts"]["do_not_numeric"],
            gpa_build["safe_match_counts"]["3.8"],
            academic_field_build["parent_rows"],
            academic_field_build["group_rows"],
            academic_field_build["classification_counts"]["single"],
            academic_field_build["classification_counts"]["multi"],
            academic_field_build["classification_counts"]["review_required"],
            academic_field_build["classification_counts"]["unmapped"],
            academic_field_build["classification_counts"]["not_applicable"],
            academic_field_build["raw_mismatch_rows"],
        )
        connection.execute(
            """
            INSERT INTO build_metadata (
                singleton_id, database_schema_version, unified_contract_version,
                unified_schema_id, build_timestamp_utc, builder_version,
                sqlite_library_version, fts5_enabled, fts_tokenizer,
                source_versions_json, input_csv_sha256_json,
                input_build_manifest_sha256, schema_sql_sha256,
                gpa_parser_contract_version, gpa_schema_sql_sha256,
                gpa_crosswalk_sha256,
                academic_field_mapping_contract_version,
                academic_field_taxonomy_version,
                academic_field_schema_sql_sha256,
                academic_field_taxonomy_sha256,
                academic_field_crosswalk_sha256,
                english_requirement_parser_contract_version,
                english_requirement_schema_sql_sha256,
                english_requirement_crosswalk_sha256,
                english_requirement_required_rows,
                english_requirement_not_required_rows,
                english_requirement_review_required_rows,
                english_requirement_unknown_rows,
                english_requirement_not_applicable_rows,
                english_requirement_unmapped_rows,
                prefecture_mapping_contract_version,
                prefecture_taxonomy_version,
                prefecture_schema_sql_sha256,
                prefecture_taxonomy_sha256,
                prefecture_crosswalk_sha256,
                prefecture_parent_rows,
                prefecture_membership_rows,
                prefecture_single_rows,
                prefecture_multi_rows,
                prefecture_unmapped_rows,
                admissions_rows, coverage_rows, research_requirements_rows,
                gpa_safe_numeric_rows, gpa_conditional_numeric_rows,
                gpa_do_not_numeric_rows, gpa_strict_match_3_8_rows,
                academic_field_parent_rows, academic_field_group_rows,
                academic_field_single_rows, academic_field_multi_rows,
                academic_field_review_required_rows,
                academic_field_unmapped_rows,
                academic_field_not_applicable_rows,
                academic_field_raw_mismatch_rows
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )

    def _validate_database(
        self,
        connection: sqlite3.Connection,
        *,
        inputs: Mapping[str, CSVInput],
        unified_manifest: Mapping[str, Any],
        input_manifest_sha: str,
        schema_sha: str,
        gpa_schema_sha: str,
        gpa_audit_sha: str,
        gpa_build: Mapping[str, Any],
        academic_field_schema_sha: str,
        academic_field_taxonomy_sha: str,
        academic_field_crosswalk_sha: str,
        academic_field_build: Mapping[str, Any],
        english_requirement_schema_sha: str,
        english_requirement_crosswalk_sha: str,
        english_requirement_build: Mapping[str, Any],
        prefecture_schema_sha: str,
        prefecture_taxonomy_sha: str,
        prefecture_crosswalk_sha: str,
        prefecture_build: Mapping[str, Any],
        capabilities: SQLiteCapabilities,
        built_at: str,
        source_versions: Mapping[str, str],
    ) -> dict[str, Any]:
        counts = self._validate_counts(connection, inputs)
        relational = self._validate_relations(connection)
        semantics = self._validate_semantics(connection)
        equality = self._validate_exact_rows(connection, inputs)
        duplicate_validation = self._validate_duplicate_preservation(
            connection, inputs["research_requirements"]
        )
        source_validation = self._validate_sources(connection, source_versions)
        views = self._validate_views(connection, counts)
        gpa = self._validate_gpa_layer(connection, counts["admissions"], gpa_build)
        academic_field = self._validate_academic_field_layer(
            connection, counts["admissions"], academic_field_build
        )
        english_requirement = self._validate_english_requirement_layer(
            connection, counts["admissions"], english_requirement_build
        )
        prefecture = self._validate_prefecture_layer(connection, counts["admissions"], prefecture_build)
        pragmas = self._validate_pragmas(connection)
        metadata = self._validate_metadata(
            connection,
            inputs=inputs,
            unified_manifest=unified_manifest,
            input_manifest_sha=input_manifest_sha,
            schema_sha=schema_sha,
            gpa_schema_sha=gpa_schema_sha,
            gpa_audit_sha=gpa_audit_sha,
            gpa_build=gpa_build,
            academic_field_schema_sha=academic_field_schema_sha,
            academic_field_taxonomy_sha=academic_field_taxonomy_sha,
            academic_field_crosswalk_sha=academic_field_crosswalk_sha,
            academic_field_build=academic_field_build,
            english_requirement_schema_sha=english_requirement_schema_sha,
            english_requirement_crosswalk_sha=english_requirement_crosswalk_sha,
            english_requirement_build=english_requirement_build,
            prefecture_schema_sha=prefecture_schema_sha,
            prefecture_taxonomy_sha=prefecture_taxonomy_sha,
            prefecture_crosswalk_sha=prefecture_crosswalk_sha,
            prefecture_build=prefecture_build,
            capabilities=capabilities,
            built_at=built_at,
            source_versions=source_versions,
        )
        fts = self._validate_fts(connection, capabilities, counts["admissions"])
        structured_queries = self._validate_structured_queries(connection)
        return {
            "status": "passed",
            "base_table_counts": counts,
            "logical_keys_and_relations": relational,
            "null_boolean_tristate_semantics": semantics,
            "source_version_and_institution_type": source_validation,
            "exact_csv_row_equality": equality,
            "research_duplicate_preservation": duplicate_validation,
            "views": views,
            "gpa_search": gpa,
            "academic_field_search": academic_field,
            "english_requirement_search": english_requirement,
            "prefecture_search": prefecture,
            "pragmas": pragmas,
            "build_metadata": metadata,
            "fts": fts,
            "structured_query_smoke_tests": structured_queries,
        }

    @staticmethod
    def _validate_counts(
        connection: sqlite3.Connection, inputs: Mapping[str, CSVInput]
    ) -> dict[str, int]:
        result: dict[str, int] = {}
        for table in TABLE_ORDER:
            sql_table = SQL_TABLES[table]
            actual = connection.execute(
                f"SELECT COUNT(*) FROM {quote_identifier(sql_table)}"
            ).fetchone()[0]
            expected = inputs[table].rows
            if actual != expected:
                raise SQLiteBuildError(
                    f"Row preservation failed for {sql_table}: "
                    f"expected={expected}, actual={actual}"
                )
            result[sql_table] = actual
        date_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_dates"
        ).fetchone()[0]
        if date_rows != 0:
            raise SQLiteBuildError("admission_search_dates must remain empty in v0.1.")
        result["admission_search_dates"] = date_rows
        return result

    @staticmethod
    def _validate_relations(connection: sqlite3.Connection) -> dict[str, Any]:
        duplicate_admissions = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT source_dataset, source_version, record_id
                FROM admissions GROUP BY 1, 2, 3 HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        duplicate_coverage = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT source_dataset, source_version, institution_type, university
                FROM coverage GROUP BY 1, 2, 3, 4 HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        orphan_children = connection.execute(
            """
            SELECT COUNT(*)
            FROM research_requirements AS r
            LEFT JOIN admissions AS a
              ON a.source_dataset = r.source_dataset
             AND a.source_version = r.source_version
             AND a.record_id = r.admission_id
            WHERE a.admission_rowid IS NULL
            """
        ).fetchone()[0]
        coverage_mismatches = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT c.coverage_rowid
                FROM coverage AS c
                LEFT JOIN admissions AS a
                  ON a.source_dataset = c.source_dataset
                 AND a.source_version = c.source_version
                 AND a.institution_type = c.institution_type
                 AND a.university = c.university
                GROUP BY c.coverage_rowid, c.master_rows
                HAVING c.master_rows <> COUNT(a.admission_rowid)
            )
            """
        ).fetchone()[0]
        missing_coverage = connection.execute(
            """
            SELECT COUNT(*)
            FROM admissions AS a
            LEFT JOIN coverage AS c
              ON c.source_dataset = a.source_dataset
             AND c.source_version = a.source_version
             AND c.institution_type = a.institution_type
             AND c.university = a.university
            WHERE c.coverage_rowid IS NULL
            """
        ).fetchone()[0]
        failures = {
            "admissions_logical_pk_duplicates": duplicate_admissions,
            "coverage_logical_key_duplicates": duplicate_coverage,
            "research_fk_orphans": orphan_children,
            "coverage_master_rows_mismatches": coverage_mismatches,
            "admissions_without_coverage": missing_coverage,
        }
        if any(failures.values()):
            raise SQLiteBuildError(f"Relational validation failed: {failures}")
        return {"status": "passed", **failures}

    @staticmethod
    def _validate_semantics(connection: sqlite3.Connection) -> dict[str, Any]:
        empty_text_cells = 0
        for table in TABLE_ORDER:
            sql_table = SQL_TABLES[table]
            for row in connection.execute(f'PRAGMA table_xinfo("{sql_table}")'):
                column = row[1]
                declared_type = row[2]
                if column == SURROGATE_COLUMNS[table] or declared_type != "TEXT":
                    continue
                count = connection.execute(
                    f"SELECT COUNT(*) FROM {quote_identifier(sql_table)} "
                    f"WHERE {quote_identifier(column)} = ''"
                ).fetchone()[0]
                empty_text_cells += count
        if empty_text_cells:
            raise SQLiteBuildError(
                f"Found {empty_text_cells} empty strings; CSV blanks must be SQL NULL."
            )

        boolean_invalid = 0
        for field in sorted(BOOLEAN_FIELDS["master"]):
            boolean_invalid += connection.execute(
                f"SELECT COUNT(*) FROM admissions WHERE {quote_identifier(field)} "
                "IS NOT NULL AND (typeof(" + quote_identifier(field) + ") <> 'integer' "
                "OR " + quote_identifier(field) + " NOT IN (0, 1))"
            ).fetchone()[0]
        integer_invalid = 0
        for table in TABLE_ORDER:
            sql_table = SQL_TABLES[table]
            for field in sorted(INTEGER_FIELDS[table]):
                integer_invalid += connection.execute(
                    f"SELECT COUNT(*) FROM {quote_identifier(sql_table)} "
                    f"WHERE {quote_identifier(field)} IS NOT NULL "
                    f"AND typeof({quote_identifier(field)}) <> 'integer'"
                ).fetchone()[0]
        tristate_invalid = 0
        for field in TRI_STATE_FIELDS:
            tristate_invalid += connection.execute(
                f"SELECT COUNT(*) FROM admissions WHERE {quote_identifier(field)} "
                "IS NOT NULL AND (typeof(" + quote_identifier(field) + ") <> 'text' "
                "OR " + quote_identifier(field) + " NOT IN ('Yes', 'No', 'Unknown'))"
            ).fetchone()[0]
        if boolean_invalid or integer_invalid or tristate_invalid:
            raise SQLiteBuildError(
                "Type/null semantics validation failed: "
                f"boolean={boolean_invalid}, integer={integer_invalid}, "
                f"tri_state={tristate_invalid}"
            )
        return {
            "status": "passed",
            "empty_text_cells": empty_text_cells,
            "invalid_boolean_cells": boolean_invalid,
            "invalid_integer_cells": integer_invalid,
            "invalid_tri_state_cells": tristate_invalid,
            "boolean_fields": sorted(BOOLEAN_FIELDS["master"]),
            "tri_state_storage": "TEXT or NULL",
        }

    def _validate_exact_rows(
        self, connection: sqlite3.Connection, inputs: Mapping[str, CSVInput]
    ) -> dict[str, Any]:
        validated: dict[str, int] = {}
        for table in TABLE_ORDER:
            item = inputs[table]
            columns = ", ".join(quote_identifier(column) for column in item.header)
            sql_table = SQL_TABLES[table]
            surrogate = SURROGATE_COLUMNS[table]
            cursor = connection.execute(
                f"SELECT {columns} FROM {quote_identifier(sql_table)} "
                f"ORDER BY {quote_identifier(surrogate)}"
            )
            count = 0
            for count, (expected, actual) in enumerate(
                zip_strict(self._iter_typed_rows(item), cursor), start=1
            ):
                actual_tuple = tuple(actual)
                if expected != actual_tuple:
                    differences = [
                        field
                        for field, left, right in zip(item.header, expected, actual_tuple)
                        if left != right
                    ]
                    raise SQLiteBuildError(
                        f"Exact row equality failed for {table} row {count}; "
                        f"columns={differences[:8]}"
                    )
            validated[sql_table] = count
        return {
            "status": "passed",
            "validated_rows": validated,
            "scope": "all unified fields, including raw and provenance fields",
        }

    def _validate_duplicate_preservation(
        self, connection: sqlite3.Connection, item: CSVInput
    ) -> dict[str, Any]:
        source_counter = Counter(self._iter_typed_rows(item))
        columns = ", ".join(quote_identifier(column) for column in item.header)
        database_counter = Counter(
            tuple(row)
            for row in connection.execute(
                f"SELECT {columns} FROM research_requirements ORDER BY research_rowid"
            )
        )
        if source_counter != database_counter:
            raise SQLiteBuildError("ResearchRequirements row multiset was not preserved.")
        source_excess = sum(count - 1 for count in source_counter.values() if count > 1)
        database_excess = sum(
            count - 1 for count in database_counter.values() if count > 1
        )
        return {
            "status": "passed",
            "input_exact_duplicate_excess_rows": source_excess,
            "database_exact_duplicate_excess_rows": database_excess,
        }

    @staticmethod
    def _validate_sources(
        connection: sqlite3.Connection, source_versions: Mapping[str, str]
    ) -> dict[str, Any]:
        declared_pairs = {(dataset, version) for dataset, version in source_versions.items()}
        table_pairs: dict[str, list[dict[str, Any]]] = {}
        observed_union: set[tuple[str, str]] = set()
        for table in ("admissions", "coverage", "research_requirements"):
            rows = connection.execute(
                f"SELECT source_dataset, source_version, COUNT(*) AS rows "
                f"FROM {table} GROUP BY 1, 2 ORDER BY 1, 2"
            ).fetchall()
            observed = {(row[0], row[1]) for row in rows}
            if not observed.issubset(declared_pairs):
                raise SQLiteBuildError(
                    f"Unexpected source/version pair in {table}: {observed - declared_pairs}"
                )
            if table in {"admissions", "coverage"}:
                observed_union.update(observed)
            table_pairs[table] = [
                {"source_dataset": row[0], "source_version": row[1], "rows": row[2]}
                for row in rows
            ]
        if observed_union != declared_pairs:
            raise SQLiteBuildError(
                "Manifest source/version pairs differ from admissions/coverage: "
                f"declared={declared_pairs}, observed={observed_union}"
            )
        institution_mismatches: dict[str, int] = {}
        for table in ("admissions", "coverage"):
            institution_mismatches[table] = connection.execute(
                f"""
                SELECT COUNT(*) FROM {table}
                WHERE NOT (
                    (source_dataset = 'kokkoritsu' AND institution_type IN ('国立','公立'))
                    OR (source_dataset = 'shidai' AND institution_type = '私立')
                )
                """
            ).fetchone()[0]
        if any(institution_mismatches.values()):
            raise SQLiteBuildError("source_dataset/institution_type mismatch found.")
        return {
            "status": "passed",
            "source_versions": dict(source_versions),
            "rows_by_table_and_source": table_pairs,
            "institution_type_mismatches": institution_mismatches,
        }

    @staticmethod
    def _validate_views(
        connection: sqlite3.Connection, counts: Mapping[str, int]
    ) -> dict[str, Any]:
        search_rows = connection.execute(
            "SELECT COUNT(*) FROM admissions_search"
        ).fetchone()[0]
        parents_with_children = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT source_dataset, source_version, admission_id
                FROM research_requirements GROUP BY 1, 2, 3
            )
            """
        ).fetchone()[0]
        expected_join_rows = (
            counts["admissions"]
            + counts["research_requirements"]
            - parents_with_children
        )
        join_rows = connection.execute(
            "SELECT COUNT(*) FROM admissions_with_research"
        ).fetchone()[0]
        if search_rows != counts["admissions"] or join_rows != expected_join_rows:
            raise SQLiteBuildError(
                "View row count validation failed: "
                f"admissions_search={search_rows}, "
                f"admissions_with_research={join_rows}, expected={expected_join_rows}"
            )
        return {
            "status": "passed",
            "admissions_search_rows": search_rows,
            "admissions_with_research_rows": join_rows,
            "admissions_with_research_expected_rows": expected_join_rows,
            "parents_with_research_children": parents_with_children,
        }

    @staticmethod
    def _validate_gpa_layer(
        connection: sqlite3.Connection,
        admissions_rows: int,
        expected: Mapping[str, Any],
    ) -> dict[str, Any]:
        parent_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_gpa"
        ).fetchone()[0]
        raw_mismatches = connection.execute(
            """
            SELECT COUNT(*)
            FROM admissions AS a
            LEFT JOIN admission_search_gpa AS g USING (admission_rowid)
            WHERE g.admission_rowid IS NULL
               OR NOT (g.raw_value IS a.gpa_requirement)
            """
        ).fetchone()[0]
        classification_counts = {
            "safe_numeric": connection.execute(
                "SELECT COUNT(*) FROM admission_search_gpa "
                "WHERE parse_status='parsed_safe'"
            ).fetchone()[0],
            "conditional_numeric": connection.execute(
                "SELECT COUNT(*) FROM admission_search_gpa "
                "WHERE parse_status='conditional_review'"
            ).fetchone()[0],
        }
        classification_counts["do_not_numeric"] = (
            parent_rows
            - classification_counts["safe_numeric"]
            - classification_counts["conditional_numeric"]
        )
        safe_view_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_gpa_safe"
        ).fetchone()[0]
        non_safe_numeric_rows = connection.execute(
            """
            SELECT COUNT(*) FROM admission_search_gpa
            WHERE parse_status <> 'parsed_safe'
              AND (gpa_min_tenths IS NOT NULL OR gpa_min_inclusive IS NOT NULL
                   OR gpa_max_tenths IS NOT NULL OR gpa_max_inclusive IS NOT NULL)
            """
        ).fetchone()[0]
        unsafe_safe_rows = connection.execute(
            """
            SELECT COUNT(*) FROM admission_search_gpa
            WHERE parse_status = 'parsed_safe'
              AND (source_value_status <> 'current'
                   OR metric_scope <> 'overall'
                   OR gpa_scale <> 'japanese_5_point'
                   OR gpa_condition_type <> 'simple_overall_minimum'
                   OR gpa_min_tenths IS NULL OR gpa_min_inclusive <> 1
                   OR gpa_max_tenths IS NOT NULL
                   OR has_subject_condition <> 0 OR has_and_condition <> 0
                   OR has_or_condition <> 0 OR has_branch_condition <> 0)
            """
        ).fetchone()[0]
        historical_safe_rows = connection.execute(
            """
            SELECT COUNT(*) FROM admission_search_gpa
            WHERE source_value_status = 'previous_year_reference'
              AND parse_status = 'parsed_safe'
            """
        ).fetchone()[0]
        group_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_gpa_rule_groups"
        ).fetchone()[0]
        clause_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_gpa_clauses"
        ).fetchone()[0]
        failures = {
            "parent_row_difference": parent_rows - admissions_rows,
            "raw_value_mismatches": raw_mismatches,
            "non_safe_rows_with_numeric_bounds": non_safe_numeric_rows,
            "unsafe_parsed_safe_rows": unsafe_safe_rows,
            "historical_parsed_safe_rows": historical_safe_rows,
            "rule_group_rows": group_rows,
            "clause_rows": clause_rows,
        }
        if any(failures.values()):
            raise SQLiteBuildError(f"GPA layer validation failed: {failures}")
        if classification_counts != expected["classification_counts"]:
            raise SQLiteBuildError(
                "GPA classification counts changed during load: "
                f"expected={expected['classification_counts']}, "
                f"actual={classification_counts}"
            )
        if safe_view_rows != classification_counts["safe_numeric"]:
            raise SQLiteBuildError("GPA safe view row count is inconsistent.")

        safe_match_counts: dict[str, int] = {}
        for tenths in GPA_REGRESSION_TENTHS:
            key = f"{tenths / 10:.1f}"
            count = connection.execute(
                """
                SELECT COUNT(*) FROM admission_search_gpa_safe AS g
                WHERE (? > g.gpa_min_tenths
                       OR (? = g.gpa_min_tenths AND g.gpa_min_inclusive = 1))
                  AND (g.gpa_max_tenths IS NULL
                       OR ? < g.gpa_max_tenths
                       OR (? = g.gpa_max_tenths AND g.gpa_max_inclusive = 1))
                """,
                (tenths, tenths, tenths, tenths),
            ).fetchone()[0]
            safe_match_counts[key] = count
        if safe_match_counts != expected["safe_match_counts"]:
            raise SQLiteBuildError(
                "GPA safe-match counts differ from parser output: "
                f"expected={expected['safe_match_counts']}, "
                f"actual={safe_match_counts}"
            )
        query_plan = [
            row[3]
            for row in connection.execute(
                "EXPLAIN QUERY PLAN SELECT admission_rowid "
                "FROM admission_search_gpa_safe WHERE gpa_min_tenths <= ?",
                (38,),
            )
        ]
        unparsed_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_gpa WHERE parse_status='unparsed'"
        ).fetchone()[0]
        return {
            "status": "passed",
            "parser_contract_version": GPA_PARSER_CONTRACT_VERSION,
            "parent_rows": parent_rows,
            "raw_value_mismatches": raw_mismatches,
            "classification_counts": classification_counts,
            "safe_view_rows": safe_view_rows,
            "safe_match_counts": safe_match_counts,
            "rule_group_rows": group_rows,
            "clause_rows": clause_rows,
            "unparsed_rows": unparsed_rows,
            "representative_unparsed_record_ids": expected[
                "representative_unparsed_record_ids"
            ],
            "query_plan_3_8": query_plan,
            "result_meaning": "overall GPA condition safely matched",
        }

    @staticmethod
    def _validate_academic_field_layer(
        connection: sqlite3.Connection,
        admissions_rows: int,
        expected: Mapping[str, Any],
    ) -> dict[str, Any]:
        parent_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_academic_fields"
        ).fetchone()[0]
        group_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_academic_field_groups"
        ).fetchone()[0]
        taxonomy_rows = connection.execute(
            "SELECT COUNT(*) FROM academic_field_taxonomy"
        ).fetchone()[0]
        raw_mismatches = connection.execute(
            """
            SELECT COUNT(*)
            FROM admissions AS a
            LEFT JOIN admission_search_academic_fields AS f
              USING (admission_rowid)
            WHERE NOT (f.raw_value IS a.academic_field)
            """
        ).fetchone()[0]
        version_mismatches = connection.execute(
            """
            SELECT COUNT(*) FROM admission_search_academic_fields
            WHERE mapping_contract_version <> ?
            """,
            (ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION,),
        ).fetchone()[0]
        taxonomy_version_mismatches = connection.execute(
            """
            SELECT COUNT(*) FROM academic_field_taxonomy
            WHERE taxonomy_version <> ?
            """,
            (ACADEMIC_FIELD_TAXONOMY_VERSION,),
        ).fetchone()[0]
        invalid_basis_rows = connection.execute(
            """
            SELECT COUNT(*) FROM admission_search_academic_field_groups
            WHERE mapping_basis <> 'exact_crosswalk'
            """
        ).fetchone()[0]
        cardinality_rows = connection.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN p.mapping_status = 'single'
                                  AND COALESCE(child_count, 0) <> 1
                                  THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN p.mapping_status = 'multi'
                                  AND COALESCE(child_count, 0) < 2
                                  THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN p.mapping_status IN (
                                      'review_required', 'unmapped', 'not_applicable'
                                  ) AND COALESCE(child_count, 0) <> 0
                                  THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN COALESCE(child_count, 0) > 0
                                  AND (minimum_order <> 1
                                       OR maximum_order <> child_count)
                                  THEN 1 ELSE 0 END), 0)
            FROM admission_search_academic_fields AS p
            LEFT JOIN (
                SELECT admission_rowid, COUNT(*) AS child_count,
                       MIN(group_order) AS minimum_order,
                       MAX(group_order) AS maximum_order
                FROM admission_search_academic_field_groups
                GROUP BY admission_rowid
            ) AS children USING (admission_rowid)
            """
        ).fetchone()
        cardinality_failures = {
            "single_wrong_child_count": cardinality_rows[0],
            "multi_wrong_child_count": cardinality_rows[1],
            "zero_child_status_wrong_child_count": cardinality_rows[2],
            "non_contiguous_group_order": cardinality_rows[3],
        }
        classification_counts = {
            row[0]: row[1]
            for row in connection.execute(
                """
                SELECT mapping_status, COUNT(*)
                FROM admission_search_academic_fields
                GROUP BY mapping_status ORDER BY mapping_status
                """
            )
        }
        classification_counts = {
            status: classification_counts.get(status, 0)
            for status in (
                "single",
                "multi",
                "review_required",
                "unmapped",
                "not_applicable",
            )
        }
        membership_counts = {
            row[0]: row[1]
            for row in connection.execute(
                """
                SELECT t.group_code, COUNT(g.admission_rowid)
                FROM academic_field_taxonomy AS t
                LEFT JOIN admission_search_academic_field_groups AS g
                  USING (group_code)
                GROUP BY t.group_code, t.display_order
                ORDER BY t.display_order
                """
            )
        }
        status_raw_counts: dict[str, dict[str, int]] = {}
        for status in ("review_required", "unmapped"):
            status_raw_counts[status] = {
                row[0]: row[1]
                for row in connection.execute(
                    """
                    SELECT raw_value, COUNT(*)
                    FROM admission_search_academic_fields
                    WHERE mapping_status = ?
                    GROUP BY raw_value ORDER BY raw_value
                    """,
                    (status,),
                )
            }
        failures = {
            "parent_row_difference": parent_rows - admissions_rows,
            "group_row_difference": group_rows - expected["group_rows"],
            "taxonomy_row_difference": taxonomy_rows - expected["taxonomy_groups"],
            "raw_value_mismatches": raw_mismatches,
            "mapping_version_mismatches": version_mismatches,
            "taxonomy_version_mismatches": taxonomy_version_mismatches,
            "invalid_mapping_basis_rows": invalid_basis_rows,
            **cardinality_failures,
        }
        if any(failures.values()):
            raise SQLiteBuildError(
                f"Academic-field layer validation failed: {failures}"
            )
        if classification_counts != expected["classification_counts"]:
            raise SQLiteBuildError(
                "Academic-field classification counts changed during load: "
                f"expected={expected['classification_counts']}, "
                f"actual={classification_counts}"
            )
        if membership_counts != expected["group_membership_counts"]:
            raise SQLiteBuildError(
                "Academic-field membership counts changed during load: "
                f"expected={expected['group_membership_counts']}, "
                f"actual={membership_counts}"
            )
        expected_status_raw_counts = {
            "review_required": expected["review_required_raw_value_counts"],
            "unmapped": expected["unmapped_raw_value_counts"],
        }
        if status_raw_counts != expected_status_raw_counts:
            raise SQLiteBuildError(
                "Academic-field review/unmapped raw counts changed during load: "
                f"expected={expected_status_raw_counts}, actual={status_raw_counts}"
            )
        query_plan = [
            row[3]
            for row in connection.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT admission_rowid
                FROM admission_search_academic_field_groups
                WHERE group_code IN (?, ?)
                ORDER BY admission_rowid
                """,
                ("engineering", "information"),
            )
        ]
        return {
            "status": "passed",
            "parent_rows": parent_rows,
            "group_rows": group_rows,
            "taxonomy_rows": taxonomy_rows,
            "raw_value_mismatches": raw_mismatches,
            "classification_counts": classification_counts,
            "group_membership_counts": membership_counts,
            "review_required_raw_value_counts": status_raw_counts[
                "review_required"
            ],
            "unmapped_raw_value_counts": status_raw_counts["unmapped"],
            "cardinality_failures": cardinality_failures,
            "mapping_basis": "exact_crosswalk",
            "query_plan_engineering_or_information": query_plan,
            "representative_unmapped_record_ids": expected[
                "representative_unmapped_record_ids"
            ],
        }

    @staticmethod
    def _validate_english_requirement_layer(
        connection: sqlite3.Connection,
        admissions_rows: int,
        build: Mapping[str, Any],
    ) -> dict[str, Any]:
        parent_rows = connection.execute(
            "SELECT COUNT(*) FROM admission_search_english_requirement"
        ).fetchone()[0]
        raw_mismatch = connection.execute(
            """
            SELECT COUNT(*) FROM admissions AS a
            JOIN admission_search_english_requirement AS e USING (admission_rowid)
            WHERE a.english_requirement IS NOT e.raw_value
            """
        ).fetchone()[0]
        statuses = dict(connection.execute(
            "SELECT requirement_status, COUNT(*) FROM admission_search_english_requirement GROUP BY requirement_status"
        ).fetchall())
        if parent_rows != admissions_rows or raw_mismatch or statuses.get("unmapped", 0):
            raise SQLiteBuildError("English requirement derived layer validation failed.")
        expected = build["classification_counts"]
        if any(statuses.get(key, 0) != value for key, value in expected.items()):
            raise SQLiteBuildError("English requirement classification counts changed.")
        return {"status": "passed", "parent_rows": parent_rows, "raw_mismatch_rows": raw_mismatch, "classification_counts": expected}

    @staticmethod
    def _validate_prefecture_layer(connection: sqlite3.Connection, admissions_rows: int, build: Mapping[str, Any]) -> dict[str, Any]:
        parent=connection.execute("SELECT COUNT(*) FROM admission_search_prefectures").fetchone()[0]
        child=connection.execute("SELECT COUNT(*) FROM admission_search_prefecture_memberships").fetchone()[0]
        mismatch=connection.execute("SELECT COUNT(*) FROM admissions a JOIN admission_search_prefectures p USING(admission_rowid) WHERE a.prefecture IS NOT p.raw_value").fetchone()[0]
        cardinality=connection.execute("""SELECT COUNT(*) FROM admission_search_prefectures p LEFT JOIN (SELECT admission_rowid,COUNT(*) n FROM admission_search_prefecture_memberships GROUP BY admission_rowid)c USING(admission_rowid) WHERE (p.mapping_status='single' AND COALESCE(c.n,0)<>1) OR (p.mapping_status='multi' AND COALESCE(c.n,0)<2) OR (p.mapping_status IN ('review_required','unmapped','not_applicable') AND COALESCE(c.n,0)<>0)""").fetchone()[0]
        statuses=dict(connection.execute("SELECT mapping_status,COUNT(*) FROM admission_search_prefectures GROUP BY mapping_status"))
        if parent!=admissions_rows or child!=build["membership_rows"] or mismatch or cardinality or statuses.get("unmapped",0): raise SQLiteBuildError("Prefecture derived layer validation failed.")
        return {"status":"passed","parent_rows":parent,"membership_rows":child,"raw_mismatch_rows":mismatch,"cardinality_failures":cardinality,"classification_counts":build["classification_counts"],"membership_counts":build["membership_counts"]}

    @staticmethod
    def _validate_pragmas(connection: sqlite3.Connection) -> dict[str, Any]:
        foreign_key_rows = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
        quick_check = [row[0] for row in connection.execute("PRAGMA quick_check")]
        if foreign_key_rows:
            raise SQLiteBuildError(f"PRAGMA foreign_key_check failed: {foreign_key_rows[:5]}")
        if quick_check != ["ok"]:
            raise SQLiteBuildError(f"PRAGMA quick_check failed: {quick_check[:5]}")
        return {
            "status": "passed",
            "foreign_key_check_rows": 0,
            "quick_check": "ok",
        }

    @staticmethod
    def _validate_metadata(
        connection: sqlite3.Connection,
        *,
        inputs: Mapping[str, CSVInput],
        unified_manifest: Mapping[str, Any],
        input_manifest_sha: str,
        schema_sha: str,
        gpa_schema_sha: str,
        gpa_audit_sha: str,
        gpa_build: Mapping[str, Any],
        academic_field_schema_sha: str,
        academic_field_taxonomy_sha: str,
        academic_field_crosswalk_sha: str,
        academic_field_build: Mapping[str, Any],
        english_requirement_schema_sha: str,
        english_requirement_crosswalk_sha: str,
        english_requirement_build: Mapping[str, Any],
        prefecture_schema_sha: str,
        prefecture_taxonomy_sha: str,
        prefecture_crosswalk_sha: str,
        prefecture_build: Mapping[str, Any],
        capabilities: SQLiteCapabilities,
        built_at: str,
        source_versions: Mapping[str, str],
    ) -> dict[str, Any]:
        rows = connection.execute("SELECT * FROM build_metadata").fetchall()
        if len(rows) != 1:
            raise SQLiteBuildError("build_metadata must contain exactly one row.")
        actual = dict(rows[0])
        expected_hashes = {
            TABLE_FILES[table]: inputs[table].sha256 for table in TABLE_ORDER
        }
        expected = {
            "singleton_id": 1,
            "database_schema_version": DATABASE_SCHEMA_VERSION,
            "unified_contract_version": unified_manifest["contract_version"],
            "unified_schema_id": unified_manifest["schema_id"],
            "build_timestamp_utc": built_at,
            "builder_version": BUILDER_VERSION,
            "sqlite_library_version": capabilities.sqlite_version,
            "fts5_enabled": int(capabilities.profile != "none"),
            "fts_tokenizer": capabilities.profile,
            "source_versions_json": canonical_json(source_versions),
            "input_csv_sha256_json": canonical_json(expected_hashes),
            "input_build_manifest_sha256": input_manifest_sha,
            "schema_sql_sha256": schema_sha,
            "gpa_parser_contract_version": GPA_PARSER_CONTRACT_VERSION,
            "gpa_schema_sql_sha256": gpa_schema_sha,
            "gpa_crosswalk_sha256": gpa_audit_sha,
            "academic_field_mapping_contract_version": (
                ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION
            ),
            "academic_field_taxonomy_version": ACADEMIC_FIELD_TAXONOMY_VERSION,
            "academic_field_schema_sql_sha256": academic_field_schema_sha,
            "academic_field_taxonomy_sha256": academic_field_taxonomy_sha,
            "academic_field_crosswalk_sha256": academic_field_crosswalk_sha,
            "english_requirement_parser_contract_version": ENGLISH_REQUIREMENT_CONTRACT_VERSION,
            "english_requirement_schema_sql_sha256": english_requirement_schema_sha,
            "english_requirement_crosswalk_sha256": english_requirement_crosswalk_sha,
            "english_requirement_required_rows": english_requirement_build["classification_counts"]["required"],
            "english_requirement_not_required_rows": english_requirement_build["classification_counts"]["not_required"],
            "english_requirement_review_required_rows": english_requirement_build["classification_counts"]["review_required"],
            "english_requirement_unknown_rows": english_requirement_build["classification_counts"]["unknown"],
            "english_requirement_not_applicable_rows": english_requirement_build["classification_counts"]["not_applicable"],
            "english_requirement_unmapped_rows": english_requirement_build["classification_counts"]["unmapped"],
            "prefecture_mapping_contract_version": PREFECTURE_MAPPING_CONTRACT_VERSION,
            "prefecture_taxonomy_version": PREFECTURE_TAXONOMY_VERSION,
            "prefecture_schema_sql_sha256": prefecture_schema_sha,
            "prefecture_taxonomy_sha256": prefecture_taxonomy_sha,
            "prefecture_crosswalk_sha256": prefecture_crosswalk_sha,
            "prefecture_parent_rows": prefecture_build["parent_rows"],
            "prefecture_membership_rows": prefecture_build["membership_rows"],
            "prefecture_single_rows": prefecture_build["classification_counts"]["single"],
            "prefecture_multi_rows": prefecture_build["classification_counts"]["multi"],
            "prefecture_unmapped_rows": prefecture_build["classification_counts"]["unmapped"],
            "admissions_rows": inputs["master"].rows,
            "coverage_rows": inputs["coverage"].rows,
            "research_requirements_rows": inputs["research_requirements"].rows,
            "gpa_safe_numeric_rows": gpa_build["classification_counts"][
                "safe_numeric"
            ],
            "gpa_conditional_numeric_rows": gpa_build["classification_counts"][
                "conditional_numeric"
            ],
            "gpa_do_not_numeric_rows": gpa_build["classification_counts"][
                "do_not_numeric"
            ],
            "gpa_strict_match_3_8_rows": gpa_build["safe_match_counts"]["3.8"],
            "academic_field_parent_rows": academic_field_build["parent_rows"],
            "academic_field_group_rows": academic_field_build["group_rows"],
            "academic_field_single_rows": academic_field_build[
                "classification_counts"
            ]["single"],
            "academic_field_multi_rows": academic_field_build[
                "classification_counts"
            ]["multi"],
            "academic_field_review_required_rows": academic_field_build[
                "classification_counts"
            ]["review_required"],
            "academic_field_unmapped_rows": academic_field_build[
                "classification_counts"
            ]["unmapped"],
            "academic_field_not_applicable_rows": academic_field_build[
                "classification_counts"
            ]["not_applicable"],
            "academic_field_raw_mismatch_rows": academic_field_build[
                "raw_mismatch_rows"
            ],
        }
        if actual != expected:
            different = sorted(
                key for key in expected if actual.get(key) != expected.get(key)
            )
            raise SQLiteBuildError(f"build_metadata mismatch: {different}")
        if json.loads(actual["source_versions_json"]) != dict(source_versions):
            raise SQLiteBuildError("build_metadata source_versions_json is invalid.")
        if json.loads(actual["input_csv_sha256_json"]) != expected_hashes:
            raise SQLiteBuildError("build_metadata input hashes are invalid.")
        return {"status": "passed", "rows": 1}

    @staticmethod
    def _validate_fts(
        connection: sqlite3.Connection,
        capabilities: SQLiteCapabilities,
        admissions_rows: int,
    ) -> dict[str, Any]:
        object_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_schema WHERE name = 'admissions_fts'"
        ).fetchone()[0]
        if capabilities.profile == "none":
            if object_count:
                raise SQLiteBuildError("FTS object exists under the no-FTS profile.")
            return {
                "status": "not_applicable",
                "enabled": False,
                "tokenizer": "none",
            }
        if object_count != 1:
            raise SQLiteBuildError("admissions_fts is missing from an FTS profile.")
        connection.execute(
            "INSERT INTO admissions_fts(admissions_fts, rank) "
            "VALUES('integrity-check', 1)"
        )
        record = connection.execute(
            """
            SELECT admission_rowid, university
            FROM admissions
            WHERE university IS NOT NULL AND length(university) >= 3
            ORDER BY admission_rowid LIMIT 1
            """
        ).fetchone()
        if record is None and admissions_rows:
            raise SQLiteBuildError("No representative FTS record is available.")
        if record is None:
            return {
                "status": "passed",
                "enabled": True,
                "tokenizer": capabilities.profile,
                "query": None,
                "matched_rowids": [],
            }
        query_text = (
            record["university"][:3]
            if capabilities.profile == "trigram"
            else record["university"]
        )
        match_query = '"' + query_text.replace('"', '""') + '"'
        matched = [
            row[0]
            for row in connection.execute(
                "SELECT rowid FROM admissions_fts "
                "WHERE admissions_fts MATCH ? ORDER BY rowid",
                (match_query,),
            )
        ]
        if record["admission_rowid"] not in matched:
            raise SQLiteBuildError(
                f"Representative FTS search did not find row {record['admission_rowid']}."
            )
        return {
            "status": "passed",
            "enabled": True,
            "tokenizer": capabilities.profile,
            "integrity_check": "passed",
            "query": query_text,
            "expected_rowid": record["admission_rowid"],
            "matched_rowids": matched[:10],
        }

    @staticmethod
    def _validate_structured_queries(
        connection: sqlite3.Connection,
    ) -> dict[str, Any]:
        sample = connection.execute(
            """
            SELECT university, institution_type, prefecture, stem_flag,
                   academic_field, exclusive_enrollment_status,
                   school_recommendation_required, common_test_required,
                   research_requirement_required, selection_oral_exam,
                   selection_interview, selection_presentation
            FROM admissions ORDER BY admission_rowid LIMIT 1
            """
        ).fetchone()
        if sample is None:
            return {"status": "passed", "queries": {}}
        specifications = {
            "university": (
                "university IS ?",
                (sample["university"],),
            ),
            "institution_type_prefecture": (
                "institution_type IS ? AND prefecture IS ?",
                (sample["institution_type"], sample["prefecture"]),
            ),
            "stem_flag_academic_field": (
                "stem_flag IS ? AND academic_field IS ?",
                (sample["stem_flag"], sample["academic_field"]),
            ),
            "exclusive_enrollment_status": (
                "exclusive_enrollment_status IS ?",
                (sample["exclusive_enrollment_status"],),
            ),
            "school_recommendation_required": (
                "school_recommendation_required IS ?",
                (sample["school_recommendation_required"],),
            ),
            "common_test_required": (
                "common_test_required IS ?",
                (sample["common_test_required"],),
            ),
            "research_requirement_required": (
                "research_requirement_required IS ?",
                (sample["research_requirement_required"],),
            ),
            "oral_interview_presentation": (
                "selection_oral_exam IS ? AND selection_interview IS ? "
                "AND selection_presentation IS ?",
                (
                    sample["selection_oral_exam"],
                    sample["selection_interview"],
                    sample["selection_presentation"],
                ),
            ),
        }
        results: dict[str, Any] = {}
        for name, (predicate, parameters) in specifications.items():
            sql = (
                "SELECT source_dataset, source_version, record_id "
                f"FROM admissions WHERE {predicate} ORDER BY admission_rowid"
            )
            plan = [
                row[3]
                for row in connection.execute("EXPLAIN QUERY PLAN " + sql, parameters)
            ]
            rows = connection.execute(sql, parameters).fetchall()
            if not rows or not plan:
                raise SQLiteBuildError(f"Structured query smoke test failed: {name}")
            results[name] = {
                "result_count": len(rows),
                "representative_record_ids": [
                    f"{row[0]}:{row[1]}:{row[2]}" for row in rows[:3]
                ],
                "query_plan": plan,
            }
        return {"status": "passed", "queries": results}

    def _build_manifest(
        self,
        *,
        inputs: Mapping[str, CSVInput],
        unified_manifest: Mapping[str, Any],
        input_manifest_sha: str,
        schema_metadata: Mapping[str, Any],
        design_metadata: Mapping[str, Any],
        gpa_schema_metadata: Mapping[str, Any],
        gpa_design_metadata: Mapping[str, Any],
        gpa_audit_metadata: Mapping[str, Any],
        gpa_build: Mapping[str, Any],
        academic_field_schema_metadata: Mapping[str, Any],
        academic_field_design_metadata: Mapping[str, Any],
        academic_field_freeze_metadata: Mapping[str, Any],
        academic_field_taxonomy_metadata: Mapping[str, Any],
        academic_field_crosswalk_metadata: Mapping[str, Any],
        academic_field_build: Mapping[str, Any],
        english_requirement_schema_metadata: Mapping[str, Any],
        english_requirement_design_metadata: Mapping[str, Any],
        english_requirement_crosswalk_metadata: Mapping[str, Any],
        english_requirement_build: Mapping[str, Any],
        prefecture_schema_metadata: Mapping[str, Any],
        prefecture_design_metadata: Mapping[str, Any],
        prefecture_taxonomy_metadata: Mapping[str, Any],
        prefecture_crosswalk_metadata: Mapping[str, Any],
        prefecture_build: Mapping[str, Any],
        capabilities: SQLiteCapabilities,
        built_at: str,
        row_counts: Mapping[str, int],
        validation: Mapping[str, Any],
        database_sha: str,
        database_size: int,
    ) -> dict[str, Any]:
        return {
            "manifest_version": "1",
            "artifact": "early_admissions_sqlite",
            "database_schema_version": DATABASE_SCHEMA_VERSION,
            "unified_contract_version": unified_manifest["contract_version"],
            "unified_schema_id": unified_manifest["schema_id"],
            "builder_version": BUILDER_VERSION,
            "build_timestamp_utc": built_at,
            "profile": {
                "name": capabilities.profile,
                **asdict(capabilities),
            },
            "source_versions": dict(unified_manifest["source_versions"]),
            "inputs": {
                "unified_build_manifest": {
                    "path": portable_manifest_path(
                        self.input_manifest_path, self.repo_root
                    ),
                    "sha256": input_manifest_sha,
                    "size_bytes": self.input_manifest_path.stat().st_size,
                },
                "unified_csv": {
                    TABLE_FILES[table]: csv_input_manifest(inputs[table], self.repo_root)
                    for table in TABLE_ORDER
                },
                "sqlite_design": dict(design_metadata),
                "sqlite_schema": dict(schema_metadata),
                "gpa_search_design": dict(gpa_design_metadata),
                "gpa_search_schema": dict(gpa_schema_metadata),
                "gpa_approved_crosswalk": dict(gpa_audit_metadata),
                "academic_field_search_design": dict(
                    academic_field_design_metadata
                ),
                "academic_field_search_schema": dict(
                    academic_field_schema_metadata
                ),
                "academic_field_mapping_freeze": dict(
                    academic_field_freeze_metadata
                ),
                "academic_field_taxonomy": dict(
                    academic_field_taxonomy_metadata
                ),
                "academic_field_crosswalk": dict(
                    academic_field_crosswalk_metadata
                ),
                "english_requirement_search_design": dict(english_requirement_design_metadata),
                "english_requirement_search_schema": dict(english_requirement_schema_metadata),
                "english_requirement_crosswalk": dict(english_requirement_crosswalk_metadata),
                "prefecture_search_design": dict(prefecture_design_metadata),
                "prefecture_search_schema": dict(prefecture_schema_metadata),
                "prefecture_taxonomy": dict(prefecture_taxonomy_metadata),
                "prefecture_crosswalk": dict(prefecture_crosswalk_metadata),
            },
            "output": {
                "path": portable_manifest_path(self.database_path, self.repo_root),
                "sha256": database_sha,
                "size_bytes": database_size,
            },
            "row_counts": dict(row_counts),
            "gpa_search": dict(gpa_build),
            "academic_field_search": dict(academic_field_build),
            "english_requirement_search": dict(english_requirement_build),
            "prefecture_search": dict(prefecture_build),
            "validation": dict(validation),
            "publication": {
                "status": "published_after_all_validations_passed",
                "journal_mode": "delete",
                "wal_sidecar": False,
                "shm_sidecar": False,
            },
            "scope_boundary": {
                "generated": ["SQLite", "build manifest", "build summary"],
                "not_generated": ["JSON search index", "Excel", "Site"],
            },
        }

    @staticmethod
    def _build_summary(manifest: Mapping[str, Any]) -> str:
        profile = manifest["profile"]
        validation = manifest["validation"]
        output = manifest["output"]
        gpa = manifest["gpa_search"]
        academic_field = manifest["academic_field_search"]
        prefecture = manifest["prefecture_search"]
        lines = [
            "# Early Admissions SQLite v0.1 build summary",
            "",
            "- Build status: `passed`",
            f"- Database schema version: `{manifest['database_schema_version']}`",
            f"- Unified contract version: `{manifest['unified_contract_version']}`",
            f"- SQLite library version: `{profile['sqlite_version']}`",
            f"- STRICT support: `{str(profile['strict']).lower()}`",
            f"- FTS profile: `{profile['profile']}`",
            f"- FTS5 / trigram: `{str(profile['fts5']).lower()}` / "
            f"`{str(profile['trigram']).lower()}`",
            f"- Database size: {output['size_bytes']} bytes",
            f"- Database SHA-256: `{output['sha256']}`",
            f"- GPA parser contract version: `{gpa['parser_contract_version']}`",
            "- Academic-field mapping/taxonomy version: "
            f"`{academic_field['mapping_contract_version']}` / "
            f"`{academic_field['taxonomy_version']}`",
            "",
            "## Row counts",
            "",
            "| Table | Rows |",
            "|---|---:|",
        ]
        for table, count in manifest["row_counts"].items():
            lines.append(f"| {table} | {count} |")
        views = validation["views"]
        lines.extend(
            [
                "",
                "## Validation",
                "",
                "- Input manifest, SHA-256, size, column count, and row count: passed",
                "- Logical PK / FK / Coverage.master_rows: passed",
                "- Null / boolean / tri-state semantics: passed",
                "- Exact CSV row, raw text, and provenance equality: passed",
                "- ResearchRequirements exact duplicate multiplicity: passed",
                f"- admissions_search rows: {views['admissions_search_rows']}",
                "- admissions_with_research rows: "
                f"{views['admissions_with_research_rows']} "
                f"(dynamic expected {views['admissions_with_research_expected_rows']})",
                "- PRAGMA foreign_key_check / quick_check: passed",
                f"- FTS validation: {validation['fts']['status']}",
                "- GPA raw-value equality, fail-closed numeric bounds, and safe view: passed",
                "- Academic-field raw equality, exact crosswalk, group enum, and cardinality: passed",
                "- Prefecture raw equality, exact crosswalk, membership FK, and cardinality: passed",
                "",
                "## GPA derived search layer",
                "",
                "| Classification | Rows |",
                "|---|---:|",
                f"| safe_numeric | {gpa['classification_counts']['safe_numeric']} |",
                f"| conditional_numeric | {gpa['classification_counts']['conditional_numeric']} |",
                f"| do_not_numeric | {gpa['classification_counts']['do_not_numeric']} |",
                "",
                "| Query GPA | Safe matches |",
                "|---:|---:|",
                *(
                    f"| {value} | {count} |"
                    for value, count in gpa["safe_match_counts"].items()
                ),
                "",
                "Result meaning: `overall GPA condition safely matched`. "
                "This is not an application-eligibility determination.",
                "",
                "## Academic-field derived search layer",
                "",
                f"- Parent rows: {academic_field['parent_rows']}",
                f"- Group rows: {academic_field['group_rows']}",
                f"- Frozen crosswalk distinct raw values: "
                f"{academic_field['crosswalk_distinct_raw_values']}",
                "",
                "| Mapping status | Admissions |",
                "|---|---:|",
                *(
                    f"| {status} | {count} |"
                    for status, count in academic_field[
                        "classification_counts"
                    ].items()
                ),
                "",
                "## Prefecture derived membership layer",
                "",
                f"- Parent rows: {prefecture['parent_rows']}",
                f"- Membership rows: {prefecture['membership_rows']}",
                f"- Frozen crosswalk distinct raw values: {prefecture['crosswalk_distinct_raw_values']}",
                f"- Mapping counts: `{canonical_json(prefecture['classification_counts'])}`",
                "",
                "| Group | Memberships |",
                "|---|---:|",
                *(
                    f"| {group} | {count} |"
                    for group, count in academic_field[
                        "group_membership_counts"
                    ].items()
                ),
                "",
                "Review-required raw values: "
                + (
                    ", ".join(
                        f"`{raw}` ({count})"
                        for raw, count in academic_field[
                            "review_required_raw_value_counts"
                        ].items()
                    )
                    or "none"
                ),
                "Unmapped raw values: "
                + (
                    ", ".join(
                        f"`{raw}` ({count})"
                        for raw, count in academic_field[
                            "unmapped_raw_value_counts"
                        ].items()
                    )
                    or "none"
                ),
                "",
                "## Representative structured queries",
                "",
                "| Query | Results | Representative record IDs | Query plan |",
                "|---|---:|---|---|",
            ]
        )
        queries = validation["structured_query_smoke_tests"]["queries"]
        for name, item in queries.items():
            records = ", ".join(f"`{value}`" for value in item["representative_record_ids"])
            plans = " / ".join(item["query_plan"]).replace("|", "\\|")
            lines.append(f"| {name} | {item['result_count']} | {records} | `{plans}` |")
        lines.extend(
            [
                "",
                "## Scope boundary",
                "",
                "This build generated only the SQLite database, its machine-readable "
                "manifest, and this summary. It did not generate a JSON search index, "
                "Excel workbook, or Site artifact.",
                "",
            ]
        )
        return "\n".join(lines)

    def _publish(self, publish_dir: Path) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(self.database_path) + suffix)
            if sidecar.exists():
                raise SQLiteBuildError(
                    f"Refusing to replace a database with a live sidecar: {sidecar}"
                )
        filenames = (DATABASE_FILENAME, "build_manifest.json", "build_summary.md")
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
            self._assert_no_sidecars(self.database_path)
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

    @staticmethod
    def _assert_no_sidecars(database: Path) -> None:
        sidecars = [Path(str(database) + suffix) for suffix in ("-wal", "-shm")]
        present = [str(path) for path in sidecars if path.exists()]
        if present:
            raise SQLiteBuildError(f"SQLite sidecar(s) remain: {', '.join(present)}")


def probe_tokenizer(
    connection: sqlite3.Connection, tokenizer: str, value: str, query: str
) -> bool:
    table = f"tokenizer_probe_{tokenizer}"
    try:
        connection.execute(
            f"CREATE VIRTUAL TABLE {table} USING fts5(value, tokenize='{tokenizer}')"
        )
        connection.execute(f"INSERT INTO {table}(value) VALUES (?)", (value,))
        matched = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {table} MATCH ?", (query,)
        ).fetchone()[0]
        return matched == 1
    except sqlite3.Error:
        return False
    finally:
        try:
            connection.execute(f"DROP TABLE IF EXISTS {table}")
        except sqlite3.Error:
            pass


def inspect_csv(path: Path, table: str) -> CSVInput:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SQLiteBuildError(f"Unified CSV contains a BOM: {path.name}")
    if b"\r" in raw:
        raise SQLiteBuildError(f"Unified CSV is not LF-only: {path.name}")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SQLiteBuildError(f"Unified CSV is not valid UTF-8: {path.name}") from error
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = tuple(next(reader))
        except StopIteration as error:
            raise SQLiteBuildError(f"Unified CSV has no header: {path.name}") from error
        rows = 0
        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise SQLiteBuildError(
                    f"CSV row width mismatch at {path}:{line_number}"
                )
            rows += 1
    return CSVInput(
        table=table,
        path=path,
        header=header,
        rows=rows,
        columns=len(header),
        size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def convert_csv_value(table: str, field: str, raw: str, line_number: int) -> Any:
    if raw == "":
        return None
    if field in BOOLEAN_FIELDS[table]:
        if raw == "true":
            return 1
        if raw == "false":
            return 0
        raise SQLiteBuildError(
            f"Invalid boolean at {TABLE_FILES[table]}:{line_number}:{field}: {raw!r}"
        )
    if field in INTEGER_FIELDS[table]:
        try:
            value = int(raw)
        except ValueError as error:
            raise SQLiteBuildError(
                f"Invalid integer at {TABLE_FILES[table]}:{line_number}:{field}: {raw!r}"
            ) from error
        if str(value) != raw:
            raise SQLiteBuildError(
                f"Non-canonical integer at {TABLE_FILES[table]}:{line_number}:"
                f"{field}: {raw!r}"
            )
        return value
    return raw


def zip_strict(
    expected: Iterable[tuple[Any, ...]], actual: Iterable[Sequence[Any]]
) -> Iterator[tuple[tuple[Any, ...], Sequence[Any]]]:
    sentinel = object()
    left = iter(expected)
    right = iter(actual)
    while True:
        left_item = next(left, sentinel)
        right_item = next(right, sentinel)
        if left_item is sentinel and right_item is sentinel:
            return
        if left_item is sentinel or right_item is sentinel:
            raise SQLiteBuildError("Exact row equality failed because row counts differ.")
        yield left_item, right_item


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def csv_input_manifest(item: CSVInput, repo_root: Path) -> dict[str, Any]:
    return {
        "path": portable_manifest_path(item.path, repo_root),
        "rows": item.rows,
        "columns": item.columns,
        "size_bytes": item.size_bytes,
        "sha256": item.sha256,
    }


def file_metadata(path: Path, repo_root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": portable_manifest_path(path, repo_root),
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def portable_manifest_path(path: Path, repo_root: Path) -> str:
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


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def write_text_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\r\n", "\n").replace("\r", "\n"))
